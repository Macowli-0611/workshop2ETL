#!/bin/bash
set -e
set -u

# Script de inicialización para crear múltiples bases de datos en PostgreSQL
function create_user_and_database() {
	local database=$1
	echo "  Creando base de datos '$database'..."
	psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
	    CREATE DATABASE $database;
	    GRANT ALL PRIVILEGES ON DATABASE $database TO $POSTGRES_USER;
EOSQL
}

if [ -n "${POSTGRES_MULTIPLE_DATABASES:-}" ]; then
	echo "Inicialización de múltiples bases de datos solicitada: $POSTGRES_MULTIPLE_DATABASES"
	for db in $(echo $POSTGRES_MULTIPLE_DATABASES | tr ',' ' '); do
		create_user_and_database $db
	done
	echo "Múltiples bases de datos creadas exitosamente."
fi
