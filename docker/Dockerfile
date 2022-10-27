FROM python:3.7-slim

ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8

# Run updates
RUN apt-get clean && apt-get update && apt-get upgrade -y

# Set the locale
RUN apt-get install -y locales && locale-gen en_US.UTF-8

COPY requirements.txt /app/requirements.txt
#Install required python packages 
RUN pip install -r /app/requirements.txt


COPY grott.py grottconf.py grottdata.py grottproxy.py grottsniffer.py /app/
RUN touch /app/grott.ini

WORKDIR /app
CMD ["python", "-u", "grott.py", "-v"]
EXPOSE 5279/tcp