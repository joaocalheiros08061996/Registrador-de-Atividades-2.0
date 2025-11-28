# src/handle_db.py
"""
Módulo de acesso a dados adaptado para Supabase (Postgres remoto).

Responsabilidades principais:
- Criar e gerenciar conexão com Supabase.
- Inicializar/verificar se a tabela de atividades existe.
- Inserir, atualizar e buscar registros de atividades.
- Calcular horas trabalhadas entre início e fim da atividade.
- Finalizar em lote atividades pendentes (usado no encerramento do app).

Observação:
As variáveis de ambiente (SUPABASE_URL / SUPABASE_KEY) devem ser
carregadas antes de chamar funções deste módulo.
"""

import os
from datetime import datetime
import logging
import pytz
from typing import Optional

# Tenta importar a biblioteca oficial do Supabase
try:
    from supabase import create_client, Client
except Exception as e:
    raise ImportError("Biblioteca 'supabase' não encontrada. Instale com: pip install supabase") from e

# Configuração de logging simples (não altera lógica; útil para diagnóstico)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Nome da tabela no Supabase
TABLE_NAME: str = "atividades"

# Definindo fuso horário padrão (America/Sao_Paulo)
TIMEZONE = pytz.timezone('America/Sao_Paulo')

# SQL para criar tabela caso não exista (referência)
CREATE_TABLE_SQL: str = f"""
CREATE TABLE IF NOT EXISTS public.{TABLE_NAME} (
  id bigserial PRIMARY KEY,
  tipo_atividade text NOT NULL,
  descricao text,
  inicio timestamp without time zone NOT NULL,
  fim timestamp without time zone,
  user_id text,
  ano integer,
  mes integer,
  dia integer,
  horas_trabalhadas numeric
);
"""


def get_supabase_client() -> Client:
    """
    Cria e retorna o cliente do Supabase usando variáveis de ambiente.

    Raises:
        RuntimeError: Se SUPABASE_URL ou SUPABASE_KEY não estiverem definidos.
    """
    url: Optional[str] = os.environ.get("SUPABASE_URL")
    key: Optional[str] = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL e SUPABASE_KEY devem estar definidas como variáveis de ambiente.")
    client: Client = create_client(url, key)
    return client


def setup_database() -> dict:
    """
    Verifica se a tabela 'atividades' existe no Supabase e retorna status.
    Caso falhe, retorna também o SQL necessário para criar a tabela.
    """
    supabase = get_supabase_client()
    try:
        # Testa se a tabela existe tentando buscar um id
        resp = supabase.table(TABLE_NAME).select("id").limit(1).execute()
        if getattr(resp, "error", None):
            logger.warning("Erro ao acessar tabela '%s': %s", TABLE_NAME, resp.error)
            return {"exists": False, "create_table_sql": CREATE_TABLE_SQL}

        # Verifica colunas adicionais necessárias (apenas aviso)
        check_columns = supabase.table(TABLE_NAME).select("ano, mes, dia, horas_trabalhadas").limit(1).execute()
        if getattr(check_columns, "error", None):
            logger.warning(
                "Tabela existe mas faltam colunas. Execute este SQL no Supabase:\n%s",
                "ALTER TABLE atividades ADD COLUMN ano integer, ADD COLUMN mes integer, "
                "ADD COLUMN dia integer, ADD COLUMN horas_trabalhadas numeric;"
            )

        logger.info("Tabela '%s' acessível no Supabase.", TABLE_NAME)
        return {"exists": True}
    except Exception as e:
        logger.exception("Falha ao verificar tabela '%s': %s", TABLE_NAME, e)
        return {"exists": False, "create_table_sql": CREATE_TABLE_SQL}


def calcular_horas_trabalhadas(inicio: datetime, fim: Optional[datetime]) -> Optional[float]:
    """
    Calcula o total de horas entre início e fim.

    Args:
        inicio (datetime): Horário inicial.
        fim (datetime | None): Horário final.

    Returns:
        float | None: Horas arredondadas em até 10 casas ou None se fim não existir.
    """
    if not fim:
        return None
    diferenca = fim - inicio
    horas = diferenca.total_seconds() / 3600
    return round(horas, 10)


def iniciar_nova_atividade(tipo: str, descricao: str, user_id: str, supabase_client: Client = None) -> Optional[int]:
    """
    Inicia uma nova atividade no Supabase e retorna o ID criado.

    Args:
        tipo (str): Tipo de atividade.
        descricao (str): Descrição da atividade.
        user_id (str): Identificador do usuário.
        supabase_client (Client, opcional): Cliente Supabase já inicializado.

    Returns:
        int | None: ID da atividade criada ou None em caso de falha.
    """
    if not supabase_client:
        supabase_client = get_supabase_client()

    hora_inicio = datetime.now(TIMEZONE)
    hora_inicio_iso: str = hora_inicio.isoformat()
    ano, mes, dia = hora_inicio.year, hora_inicio.month, hora_inicio.day

    payload = {
        "tipo_atividade": tipo,
        "descricao": descricao,
        "inicio": hora_inicio_iso,
        "user_id": user_id,
        "ano": ano,
        "mes": mes,
        "dia": dia,
        "horas_trabalhadas": None
    }

    resp = supabase_client.table(TABLE_NAME).insert(payload).execute()
    if getattr(resp, "error", None):
        logger.error("Erro ao inserir atividade: %s", resp.error)
        raise RuntimeError(f"Supabase insert error: {resp.error}")

    data = getattr(resp, "data", None)
    if data and isinstance(data, list) and len(data) > 0:
        inserted = data[0]
        return inserted.get("id", None)
    return None


def finalizar_atividade(activity_id: int, supabase_client: Client = None) -> bool:
    """
    Finaliza uma atividade no Supabase calculando horas trabalhadas.

    Args:
        activity_id (int): ID da atividade a ser finalizada.
        supabase_client (Client, opcional): Cliente Supabase já inicializado.

    Returns:
        bool: True se atualização foi bem sucedida.
    """
    if not supabase_client:
        supabase_client = get_supabase_client()

    # Busca atividade para obter início
    atividade = supabase_client.table(TABLE_NAME).select("inicio").eq("id", activity_id).execute()
    if getattr(atividade, "error", None):
        logger.error("Erro ao buscar atividade id=%s: %s", activity_id, atividade.error)
        raise RuntimeError(f"Supabase select error: {atividade.error}")
    if not atividade.data:
        logger.error("Atividade id=%s não encontrada.", activity_id)
        raise RuntimeError("Atividade não encontrada.")

    # Converte string ISO para datetime e aplica timezone
    inicio_str: str = atividade.data[0]["inicio"]
    inicio: datetime = datetime.fromisoformat(inicio_str.replace('Z', '+00:00')).astimezone(TIMEZONE)

    fim: datetime = datetime.now(TIMEZONE)
    fim_iso: str = fim.isoformat()
    horas_trabalhadas: Optional[float] = calcular_horas_trabalhadas(inicio, fim)

    # Atualiza atividade com horário de fim
    resp = supabase_client.table(TABLE_NAME).update({
        "fim": fim_iso,
        "horas_trabalhadas": horas_trabalhadas
    }).eq("id", activity_id).execute()

    if getattr(resp, "error", None):
        logger.error("Erro ao finalizar atividade id=%s: %s", activity_id, resp.error)
        raise RuntimeError(f"Supabase update error: {resp.error}")
    logger.info("Atividade id=%s finalizada (horas=%s)", activity_id, horas_trabalhadas)
    return True


def buscar_atividade_em_andamento(user_id: Optional[str] = None, supabase_client: Client = None) -> Optional[dict]:
    """
    Busca a última atividade em andamento (sem horário de fim).

    Args:
        user_id (str | None): Usuário específico para filtro (opcional).
        supabase_client (Client, opcional): Cliente Supabase.

    Returns:
        dict | None: Dados da atividade ou None se não houver.
    """
    if not supabase_client:
        supabase_client = get_supabase_client()

    query = supabase_client.table(TABLE_NAME).select("*").is_("fim", None).order("id", desc=True).limit(1)
    if user_id is not None:
        query = query.eq("user_id", user_id)

    resp = query.execute()
    if getattr(resp, "error", None):
        logger.error("Erro ao buscar atividade em andamento: %s", resp.error)
        raise RuntimeError(f"Supabase select error: {resp.error}")

    data = getattr(resp, "data", None)
    if data and isinstance(data, list) and len(data) > 0:
        return data[0]
    return None


def listar_atividades(limit: int = 100, user_id: Optional[str] = None, supabase_client: Client = None) -> list:
    """
    Lista atividades do Supabase, ordenadas por ID decrescente.

    Args:
        limit (int): Número máximo de atividades a retornar.
        user_id (str | None): Usuário específico para filtro.
        supabase_client (Client, opcional): Cliente Supabase.

    Returns:
        list[dict]: Lista de atividades.
    """
    if not supabase_client:
        supabase_client = get_supabase_client()

    query = supabase_client.table(TABLE_NAME).select("*").order("id", desc=True).limit(limit)
    if user_id is not None:
        query = query.eq("user_id", user_id)
    resp = query.execute()

    if getattr(resp, "error", None):
        logger.error("Erro ao listar atividades: %s", resp.error)
        raise RuntimeError(f"Supabase select error: {resp.error}")
    return getattr(resp, "data", []) or []


import threading


def finalizar_atividades_em_andamento(supabase_client: Client = None) -> int:
    """
    Finaliza todas as atividades que estiverem sem 'fim' (fim IS NULL).
    Retorna o número de atividades finalizadas com sucesso.

    Observações:
    - Usa get_supabase_client() se supabase_client não for fornecido.
    - Reutiliza finalizar_atividade(...) para garantir cálculo de horas.
    - Pode falhar se não houver rede no momento do encerramento.
    """
    if not supabase_client:
        try:
            supabase_client = get_supabase_client()
        except Exception as e:
            logger.exception("Não foi possível criar Supabase client ao finalizar atividades: %s", e)
            return 0

    try:
        # busca ids das atividades sem fim
        resp = supabase_client.table(TABLE_NAME).select("id").is_("fim", None).execute()
        if getattr(resp, "error", None):
            logger.error("Erro ao buscar atividades em andamento: %s", resp.error)
            return 0

        rows = getattr(resp, "data", []) or []
        ids = [r["id"] for r in rows if "id" in r]

        sucesso = 0
        for act_id in ids:
            try:
                # chama sua função existente que já calcula horas e faz update
                finalizar_atividade(act_id, supabase_client=supabase_client)
                sucesso += 1
            except Exception as e:
                logger.exception("Falha ao finalizar atividade id=%s: %s", act_id, e)
                # continua tentando as próximas
        logger.info("Finalização em lote concluída: %d finalizadas, %d falhas (total=%d).",
                    sucesso, len(ids) - sucesso, len(ids))
        return sucesso
    except Exception as e:
        logger.exception("Erro inesperado em finalizar_atividades_em_andamento: %s", e)
        return 0
