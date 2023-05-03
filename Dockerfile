FROM python:3.7-slim

ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8

# Run updates
RUN apt-get clean && apt-get update && apt-get upgrade -y

# Set the locale
RUN apt-get install -y locales && locale-gen en_US.UTF-8

#Install required python packages 
RUN pip install paho-mqtt
RUN pip install requests 
RUN pip install influxdb
RUN pip install influxdb-client 

COPY grott.py /app/grott.py
COPY grottconf.py /app/grottconf.py
COPY grottdata.py /app/grottdata.py
COPY grottproxy.py /app/grottproxy.py
COPY grottsniffer.py /app/grottsniffer.py
COPY grott.ini /app/grott.ini

WORKDIR /app
CMD ["python", "-u", "grott.py", "-v"]