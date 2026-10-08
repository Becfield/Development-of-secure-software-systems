FROM postgres:18

RUN apt-get update \
    && apt-get install -y locales \
    && sed -i '/ru_RU.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/*

COPY init.sh    /docker-entrypoint-initdb.d/01_init.sh
COPY init.sql   /docker-entrypoint-initdb.d/init.sql
COPY seed.sql   /docker-entrypoint-initdb.d/seed.sql

RUN chmod +x /docker-entrypoint-initdb.d/01_init.sh
