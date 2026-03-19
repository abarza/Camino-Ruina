FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    cron \
    curl \
    git \
    python3 \
    python3-venv \
    tmux \
    xvfb \
    libsdl2-2.0-0 \
    libsdl2-image-2.0-0 \
    libsdl2-ttf-2.0-0 \
    libsdl2-mixer-2.0-0 \
    libopenal1 \
    imagemagick \
    x11vnc \
    xdotool \
    openbox \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /gonzalo

COPY requirements.txt /gonzalo/requirements.txt

# Crear un virtualenv propio dentro del contenedor y usarlo para todo.
RUN python3 -m venv /venv && /venv/bin/pip install --no-cache-dir -r /gonzalo/requirements.txt
ENV PATH="/venv/bin:${PATH}"

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

COPY docker/launch_df.sh /usr/local/bin/launch_df.sh
RUN chmod +x /usr/local/bin/launch_df.sh

COPY docker/cron_narrador /etc/cron.d/cron_narrador
RUN chmod 0644 /etc/cron.d/cron_narrador && crontab /etc/cron.d/cron_narrador

COPY scripts /gonzalo/scripts

ENV DISPLAY=:99
ENV MUNDO_DIR=/gonzalo/mundo
ENV TMUX_SESSION=df
ENV TMUX_PANE=0
ENV DF_DIR=/opt/df
ENV DF_CMD=./dwarfort

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
