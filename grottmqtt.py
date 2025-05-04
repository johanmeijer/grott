import logging
from concurrent.futures import ThreadPoolExecutor
import paho.mqtt.client as mqtt
import socket
import time

logger = logging.getLogger(__name__)

class MQTTPublisher:
    def __init__(self, hostname, port, client_id, auth=None, socket_timeout=1.0):
        """
        Initialize the MQTT publisher.

        Args:
            hostname (str): MQTT broker hostname or IP address.
            port (int): MQTT broker port (e.g., 1883).
            client_id (str): Unique client ID for the MQTT connection.
            auth (dict, optional): Dictionary with 'username' and 'password' for authentication.
            socket_timeout (float): Socket timeout in seconds for MQTT operations (default: 1.0).
        """
        self.hostname = hostname
        self.port = port
        self.client_id = client_id
        self.auth = auth
        self.socket_timeout = socket_timeout
        logger.debug("initializing MQTT")

        # Create and configure the MQTT client
        self.client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311)
        if self.auth:
            self.client.username_pw_set(self.auth['username'], self.auth['password'])
#        self.client.socket().settimeout(self.socket_timeout)

    def publish(self, topic, payload, qos=0, retain=False, timeout=1.0):
        """
        Publish an MQTT message with a timeout.

        Args:
            topic (str): MQTT topic to publish to.
            payload (str): Message payload (e.g., JSON string).
            qos (int): Quality of Service level (0, 1, or 2; default: 0).
            retain (bool): Whether to retain the message on the broker (default: False).
            timeout (float): Maximum time to wait for the publish operation (default: 1.0 seconds).

        Returns:
            bool: True if the publish succeeded, False if it failed (e.g., due to timeout or error).
        """
        def publish_message():
            start_time = time.time()
            logger.debug("Starting MQTT publish to topic: %s", topic)
            try:
                self.client.connect(self.hostname, self.port, keepalive=60)
                sock = self.client.socket()
                if sock is not None:
                     sock.settimeout(self.socket_timeout)
                     logger.debug("Socket timeout set to %.2f seconds", self.socket_timeout)
                else:
                     logger.error("No socket available after connect for topic: %s", topic)
                     raise RuntimeError("MQTT client has no socket")
                # Publish the message
                self.client.publish(topic, payload=payload, qos=qos, retain=retain)
                logger.debug("Publish completed in %.2f seconds", time.time() - start_time)
            except Exception as e:
	            logger.debug("MQTT message error : %s", e)
            finally:
                self.client.disconnect()
                logger.debug("MQTT client disconnected")

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(publish_message)
                future.result(timeout=timeout)
            logger.debug("MQTT message published successfully to topic: %s", topic)
            return True
        except TimeoutError:
            logger.debug("MQTT Timeout occurred while publishing to topic: %s", topic)
            try:
                self.client.disconnect()
            except:
                pass
            return False
        except ConnectionRefusedError:
            logger.debug("Connection refused by MQTT broker for topic: %s", topic)
            return False
        except socket.timeout:
            logger.debug("MQTT Socket timeout while publishing to topic: %s", topic)
            return False
        except Exception as e:
            logger.debug("Exception in MQTT publish: %s", e)
            return False
        finally:
            try:
                self.client.disconnect()
                logger.debug("Final cleanup: MQTT client disconnected")
            except:
                pass

    def __del__(self):
        """
        Destructor to ensure the MQTT client is disconnected when the object is destroyed.
        """
        try:
            self.client.disconnect()
        except:
            pass
