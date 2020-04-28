from application.Program import create_mc_app,create_admin_app
from application.Config import SetAdmin

if __name__ == "__main__":
	#mcProgram = create_mc_app().run(host="0.0.0.0",debug=False, threaded=True)
	SetAdmin(True)
	print("RUNNING ADMIN SERVICE");adminProgram = create_admin_app().run(host="0.0.0.0",port=8000,debug=False, threaded=True)