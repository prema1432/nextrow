.PHONY: help build run stop rm logs shell restart status

APP_NAME ?= adobe-scanner
PORT ?= 80
CONTAINER_PORT ?= 8000
DOCKER ?= docker
MONGO_URI ?=

help:
	@echo "Targets:"
	@echo "  make build        - Build Docker image"
	@echo "  make run          - Run container (detached)"
	@echo "  make logs         - Tail container logs"
	@echo "  make stop         - Stop container"
	@echo "  make rm           - Remove container"
	@echo "  make restart      - Stop+remove+rebuild+run"
	@echo "  make status       - Docker ps filtered by name"
	@echo "  make shell        - Shell into running container"
	@echo ""
	@echo "Vars: APP_NAME=$(APP_NAME) PORT=$(PORT) CONTAINER_PORT=$(CONTAINER_PORT) DOCKER=\"$(DOCKER)\""
	@echo "Local dev tip: if port 80 is busy, run with PORT=8000"
	@echo "EC2 tip: if Docker requires sudo, run with DOCKER=\"sudo docker\""
	@echo "Mongo tip: pass MONGO_URI env with MONGO_URI=\"...\" (optional)"

build:
	$(DOCKER) build -t $(APP_NAME) .

run:
	- $(DOCKER) rm -f $(APP_NAME)
	$(DOCKER) run -d \
		--name $(APP_NAME) \
		--restart always \
		-p $(PORT):$(CONTAINER_PORT) \
		$(if $(MONGO_URI),-e MONGO_URI="$(MONGO_URI)",) \
		$(APP_NAME)

logs:
	$(DOCKER) logs -f $(APP_NAME)

stop:
	- $(DOCKER) stop $(APP_NAME)

rm:
	- $(DOCKER) rm $(APP_NAME)

restart: stop rm build run

status:
	$(DOCKER) ps --filter "name=$(APP_NAME)"

shell:
	$(DOCKER) exec -it $(APP_NAME) /bin/sh
