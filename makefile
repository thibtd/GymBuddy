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
	pylint --disable=C,W0718,R0914,R1702,R0912,R0915,R0902,R0801,E1101,W0108 \
	 *.py modules/**/*.py modules/*.py

llm: ## call to ollama to pull the model mentioned by $(MODEL)
	@echo "starting ollama..."
	open -a Ollama
	@echo "Waiting for Ollama to start..."
	sleep 5
	@echo "Checking if model $(MODEL) is already pulled..."
	ollama list | grep $(MODEL) || \
		( echo "Model $(MODEL) not found, pulling..." && \
		ollama pull $(MODEL) )
	@echo "Model $(MODEL) is ready to use."


run_test: ## run the app with fatsapi for testing (reloading)
	uvicorn main:app --reload

run_docker: ## run the app in a docker container
	@echo "Starting Docker Daemon"
	open -a Docker
	@echo "Waiting for Docker to start..."
	sleep 5
	@echo "Building and running the Docker container..."
	docker compose up --build

all: ## Install dependencies, run tests, format code, and lint. 
	install test format lint 