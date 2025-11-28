# src/main.py
"""
Entrypoint da aplicação.

Este módulo prepara o ambiente (carrega .env e registra caminhos de recursos)
e em seguida inicializa e executa a aplicação Kivy/KivyMD definida em
src.functions.ActivityTrackerApp.

Além disso, registra mecanismos para tentar finalizar atividades pendentes
quando o aplicativo é encerrado (atexit, sinais, on_stop wrapper e
on_request_close da janela). A estratégia tenta ser segura e não bloquear
desnecessariamente o encerramento da UI, mas dá uma janela curta para que
a finalização em lote ocorra.
"""
import sys
import atexit
import signal
import threading

from typing import List
import src.functions as fn  # type: ignore

from kivy.core.window import Window

# Tentativa de importar handle_db de forma compatível com execução como pacote ou arquivo
try:
    from src import handle_db as db  # type: ignore
except Exception:
    try:
        import handle_db as db  # type: ignore
    except Exception as e:
        raise ImportError(
            "Não foi possível importar 'handle_db'. Verifique se handle_db.py está em 'src/' "
            "ou na raiz do projeto."
        ) from e


def _finalize_ativos_threaded() -> None:
    """
    Inicia uma thread daemon que executa finalizar_atividades_em_andamento().
    Não bloqueia o encerramento do processo — usado em atexit/sinais e em on_stop wrapper
    para não travar o fluxo de desligamento da UI.
    """
    try:
        t = threading.Thread(target=db.finalizar_atividades_em_andamento, daemon=True)
        t.start()
    except Exception as e:
        print("[main] falha ao iniciar finalização em thread (daemon):", e)


def _finalize_ativos_blocking(timeout: float = 3.0) -> None:
    """
    Inicia uma thread NÃO-daemon para finalizar atividades e aguarda até `timeout` segundos.
    Usado em on_request_close (fechar janela) para dar maior chance de completar as operações.
    """
    try:
        t = threading.Thread(target=db.finalizar_atividades_em_andamento, daemon=False)
        t.start()
        t.join(timeout=timeout)
        if t.is_alive():
            print(f"[main] finalização em lote não terminou após {timeout}s; seguindo com encerramento.")
        else:
            print("[main] finalização em lote terminou antes do encerramento.")
    except Exception as e:
        print("[main] erro ao rodar finalização bloqueante:", e)


def main(args: list) -> None:
    """
    Função principal que prepara o ambiente e executa a aplicação.
    Passos:
    1) adicionar_caminhos_kv()
    2) carregar_env()
    3) carregar_arquivos_kv()
    4) instanciar e executar ActivityTrackerApp
    """
    # 1) Registrar caminhos de recursos (essencial para builds onefile do PyInstaller).
    try:
        fn.adicionar_caminhos_kv()
    except Exception as e:
        print(f"[AVISO] falha em adicionar caminhos KV: {e}")

    # 2) Carregar variáveis de ambiente (.env)
    try:
        fn.carregar_env()
    except Exception as e:
        print(f"[AVISO] falha ao carregar .env: {e}")

    # 3) Carregar arquivos .kv que definem os layouts (login.kv, main.kv)
    try:
        fn.carregar_arquivos_kv()
    except Exception as e:
        print(f"[ERRO] falha ao carregar arquivos KV: {e}", file=sys.stderr)

    # 4) Instanciar e executar a aplicação
    try:
        app = fn.ActivityTrackerApp()  # instanciar a app (constrói tema e telas no build())

        # ---------- on_stop wrapper (não-bloqueante) ----------
        # Mantemos um wrapper que dispara a finalização em thread daemon quando a App para.
        # Isso evita dependência exclusiva dos sinais/atexit e permite tentativa rápida.
        try:
            _orig_on_stop = app.on_stop

            def _on_stop_wrapper(*args, **kwargs):
                try:
                    # disparar versão NÃO-bloqueante para não travar o ciclo de desligamento
                    _finalize_ativos_threaded()
                except Exception as e:
                    print("[main] erro no on_stop ao finalizar atividades:", e)
                try:
                    return _orig_on_stop(*args, **kwargs)
                except Exception:
                    return None

            app.on_stop = _on_stop_wrapper
        except Exception:
            # Se não for possível sobrescrever, seguimos sem interromper
            pass

        # Registrar finalização via atexit e sinais POSIX (fallbacks adicionais)
        atexit.register(_finalize_ativos_threaded)
        try:
            signal.signal(signal.SIGINT, lambda signum, frame: _finalize_ativos_threaded())
            signal.signal(signal.SIGTERM, lambda signum, frame: _finalize_ativos_threaded())
        except Exception:
            # Em alguns ambientes (ex.: Windows GUI) registro de sinais pode falhar — ignoramos.
            pass

        # ---------- Handler de fechamento da janela (X) ----------
        # Ao clicar no X, tentamos uma finalização bloqueante (espera curta).
        def _on_request_close(window, *largs):
            try:
                # aguarda até 5 segundos para tentar finalizar as atividades pendentes
                _finalize_ativos_blocking(timeout=5.0)
            except Exception as e:
                print("[main] erro em on_request_close:", e)
            # retornar False permite que a janela seja fechada
            return False

        try:
            Window.bind(on_request_close=_on_request_close)
        except Exception as e:
            print("[main] não foi possível bindar on_request_close:", e)

        # Inicia loop principal do Kivy (bloqueante)
        app.run()

    except KeyboardInterrupt:
        # usuário pressionou Ctrl+C no console; tentar finalizar e sair graciosamente
        print("Execução interrompida pelo usuário (KeyboardInterrupt). Tentando finalizar atividades...")
        try:
            _finalize_ativos_blocking(timeout=3.0)
        except Exception:
            pass
    except Exception as exc:
        # qualquer exceção não prevista: logar e sair com código de erro
        print(f"[ERRO FATAL] durante execução da app: {exc}", file=sys.stderr)
        sys.exit(1)

    # Encerrar o processo com sucesso (0)
    sys.exit(0)


if __name__ == '__main__':
    main(sys.argv[1:])
