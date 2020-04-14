from application.Program import create_app

if __name__ == "__main__":
	program = create_app().run(host="0.0.0.0",debug=False)