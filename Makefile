# Nusantara Mini ERP - developer shortcuts (Docker based).
# Usage: make <target> [DB=name] [MODULES=a,b]

DB ?= nme
TEST_DB ?= nme_test
MODULES ?= nme_base,nme_inventory,nme_sales,nme_purchase,nme_invoicing,nme_reporting
TEST_TAGS ?= $(shell echo "/$(MODULES)" | sed 's/,/,\//g')

COMPOSE := docker compose
ODOO := $(COMPOSE) run --rm odoo odoo

.PHONY: help up down logs install upgrade test coverage lint shell psql reset-test-db

help:
	@echo "Targets: up down logs install upgrade test coverage lint shell psql"
	@echo "Variables: DB=$(DB) TEST_DB=$(TEST_DB) MODULES=$(MODULES)"

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f odoo

install:
	$(ODOO) -d $(DB) -i $(MODULES) --with-demo --stop-after-init

upgrade:
	$(ODOO) -d $(DB) -u $(MODULES) --stop-after-init

reset-test-db:
	$(COMPOSE) up -d db
	$(COMPOSE) exec db dropdb -U odoo --if-exists $(TEST_DB)

test: reset-test-db
	$(ODOO) -d $(TEST_DB) -i $(MODULES) --test-tags=$(TEST_TAGS) --stop-after-init

coverage: reset-test-db
	$(COMPOSE) run --rm --user root --entrypoint bash odoo -c "\
		apt-get update -qq && apt-get install -y -qq python3-coverage > /dev/null && \
		cd /tmp && python3-coverage run --source=/mnt/extra-addons \
			--omit='*/tests/*,*/__manifest__.py' /usr/bin/odoo \
			--db_host=db --db_user=odoo --db_password=odoo -c /etc/odoo/odoo.conf \
			-d $(TEST_DB) -i $(MODULES) --test-tags=$(TEST_TAGS) --stop-after-init && \
		python3-coverage report -m"

lint:
	pre-commit run --all-files

shell:
	$(ODOO) shell -d $(DB)

psql:
	$(COMPOSE) exec db psql -U odoo -d $(DB)
