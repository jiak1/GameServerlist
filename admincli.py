from application.Program import create_admin_app
from application.Config import SetAdmin

SetAdmin(True)
adminProgram = create_admin_app()