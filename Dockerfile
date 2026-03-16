FROM python:3.11.5

WORKDIR /usr/src/app

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY src/ src/

CMD [ "python", "-u", "./src/server.py" ]
