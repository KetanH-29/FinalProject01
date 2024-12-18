from pyspark.sql import SparkSession
from pyspark.sql.functions import *
import yaml
import os.path
import utils.aws_utils as ut

if __name__ == '__main__':

    #os.environ["PYSPARK_SUBMIT_ARGS"] = (
    #    '--packages "org.mongodb.spark:mongo-spark-connector_2.11:2.4.1" pyspark-shell'
    #)
    current_dir = os.path.abspath(os.path.dirname(__file__))
    pem_file_path = os.path.join(current_dir, "your_pem_file.pem")
    app_config_path = os.path.abspath(current_dir + "../../" + "application.yml")
    app_secrets_path = os.path.abspath(current_dir + "/" + ".secrets")

    conf = open(app_config_path)
    app_conf = yaml.load(conf, Loader=yaml.FullLoader)
    secret = open(app_secrets_path)
    app_secret = yaml.load(secret, Loader=yaml.FullLoader)

    # create the spark object
    spark = SparkSession \
        .builder \
        .appName("Read ingestion enterprise applications") \
        .config("spark.mongodb.input.uri", app_secret["mongodb_conf"]["uri"])\
        .getOrCreate()

    # to log only the error logs in the console
    spark.sparkContext.setLogLevel('ERROR')

    # Reading Data from S3
    hadoop_conf = spark.sparkContext._jsc.hadoopConfiguration()
    hadoop_conf.set("fs.s3a.access.key", app_secret["s3_conf"]["access_key"])
    hadoop_conf.set("fs.s3a.secret.key", app_secret["s3_conf"]["secret_access_key"])


    src_list = app_conf["source_list"]
    for src in src_list:
        src_conf = app_conf[src]

        src_path = "s3a://" + app_conf["s3_conf"]["s3_bucket"] + "/" + app_conf["s3_conf"]["staging_dir_loc"] + "/" + src
        if src == 'SB':
            txn_df = ut.read_from_mysql(spark,
                                        src_conf["mysql_conf"]["dbtable"],
                                        src_conf["mysql_conf"]["partition_column"],
                                        app_secret)

            txn_df = txn_df.withColumn("ins_dt", current_date())
            txn_df.show(5, False)
            # write data to S3 in parquet format
            txn_df\
                .write \
                .mode("overwrite") \
                .partitionBy("ins_dt") \
                .parquet(src_path)


        elif src == 'OL':

            # Reading Data from SFTP server
            print(src_conf["sftp_conf"]["directory"])
            txn_df = ut.read_from_sftp(
                spark,
                app_secret,
                os.path.abspath(current_dir + "/../../" + app_secret["sftp_conf"]["pem"]),
                src_conf["sftp_conf"]["directory"] + "/receipts_delta_GBR_14_10_2017.csv"
            )

            txn_df = txn_df.withColumn("ins_dt", current_date())
            txn_df.show(5, False)
            # write data to S3 in parquet format
            txn_df\
                .write \
                .mode("overwrite") \
                .partitionBy("ins_dt") \
                .parquet(src_path)

        elif src == 'CP':
            txn_df = ut.read_from_s3(spark,
                                "s3a://" + app_conf["s3_conf"]["s3_bucket"] + src_conf["filename"])
            cust_df = txn_df.withColumn("ins_dt", current_date())
            cust_df.show(5)
            # write data to S3
            cust_df \
                .write \
                .mode("overwrite") \
                .partitionBy("ins_dt") \
                .parquet(src_path)

        elif src == 'ADDR':
            # Reading from mongodb
            txn_df = ut.read_from_mongoDB(spark,
                                          src_conf["mongodb_config"]["database"],
                                          src_conf["mongodb_config"]["collection"])
            txn_df = txn_df.withColumn("ins_dt", current_date())
            txn_df.show(5)

            txn_df = txn_df.withColumn("street", col("address.street"))\
                .withColumn("City", col("address.city"))\
                .withColumn("state", col("address.state"))\
                .drop('address')\
                .drop('_id')

            txn_df.show(5)
            # write data to S3
            txn_df \
                .write \
                .mode("overwrite") \
                .partitionBy("ins_dt") \
                .parquet(src_path)



# spark-submit --packages "org.mongodb.spark:mongo-spark-connector_2.11:2.4.1,mysql:mysql-connector-java:8.0.15,com.springml:spark-sftp_2.11:1.1.1,org.apache.hadoop:hadoop-aws:2.7.4" com/ETL/source_data_loading.py

# spark-submit   --packages  "org.mongodb.spark:mongo-spark-connector_2.11:2.2.2,org.apache.hadoop:hadoop-aws:2.7.4" com/ETL/source_data_loading.py