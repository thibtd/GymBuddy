help:     ## Show this help.
	@sed -ne '/@sed/!s/## //p' $(MAKEFILE_LIST)

install:  ## Install dependencies.
	pip install --upgrade pip &&\
		pip install -r requirements.txt

test: ## Run tests with pytest.
	python -m pytest -vvv
	
format: ## Format code with black.
	black . ./**/*.py


lint: ## Lint code with pylint.
	pylint --disable=R,C,E1101,E0611 \
	 --extension-pkg-whitelist=mediapipe \
	 *.py modules/**/*.py

run_test: ## run the app with fatsapi for testing (reloading)
	uvicorn main:app --reload

all: ## Install dependencies, run tests, format code, and lint. 
	install test format lint 