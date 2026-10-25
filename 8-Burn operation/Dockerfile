FROM python:3.12-slim
RUN pip install --no-cache-dir esptool==5.1.0 pyserial
WORKDIR /burn
COPY flash.py .
# "Burn files/" is mounted at runtime so new images don't need a rebuild
ENTRYPOINT ["python3", "/burn/flash.py"]
