FROM postgres:18

RUN apt-get update \
    && apt-get install -y locales \
    && sed -i '/ru_RU.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/*
