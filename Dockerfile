FROM bitnami/spark:3.4.1

USER root

# Copy requirements file from the host to the container
COPY requirements.txt /opt/bitnami/spark/requirements.txt

# Installing Python dependencies
RUN pip install --no-cache-dir -r /opt/bitnami/spark/requirements.txt

# Adding Hadoop AWS and PostgreSQL JDBC driver to Spark's classpath
ADD https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar /opt/bitnami/spark/jars/
ADD https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar /opt/bitnami/spark/jars/
ADD https://jdbc.postgresql.org/download/postgresql-42.6.0.jar /opt/bitnami/spark/jars/

# Security: Switching back to a non-root user for execution
USER 1001