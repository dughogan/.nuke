# Built-in
import sys

# External
from app_manager.nuke_executer import NukeExecuter
from pipe_core.pipe_context import PipeContext

AUTO_CONTACT_SHEETS_SCRIPT = '$PKG_NUKE_ARTIST_TOOLS/plutonium/contact_sheets/auto_contact_sheets.py'

def main():
    """runs auto contact sheets"""
    context = PipeContext.from_env()
    executer = NukeExecuter(context,
                            py_script=AUTO_CONTACT_SHEETS_SCRIPT,
                            batch_mode=True,
                            pkgs_use_env=True,
                            py_args=[],
                            verbosity=0)
    return executer.execute().wait()

if __name__ == '__main__':
    sys.exit(main())
