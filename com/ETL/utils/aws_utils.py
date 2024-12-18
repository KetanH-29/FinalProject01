def get_redshift_jdbc_url(redshift_config: dict):
    host = redshift_config["redshift_conf"]["host"]
    port = redshift_config["redshift_conf"]["port"]
    database = redshift_config["redshift_conf"]["database"]
    username = redshift_config["redshift_conf"]["username"]
    password = redshift_config["redshift_conf"]["password"]
    return "jdbc:redshift://{}:{}/{}?user={}&password={}".format(host, port, database, username, password)


# we have to write a function that takes all the necessary info, read data from mysql and return a dataframe

def get_mysql_jdbc_url(mysql_config: dict):
    host = mysql_config["mysql_conf"]["hostname"]
    port = mysql_config["mysql_conf"]["port"]
    database = mysql_config["mysql_conf"]["database"]
    return "jdbc:mysql://{}:{}/{}?autoReconnect=true&useSSL=false".format(host, port, database)


def read_from_mysql(spark, table_name, part_col, secret_conf):
    print("\nReading data from MYSQL DB,")
    jdbc_params = {"url": get_mysql_jdbc_url(secret_conf),
                   "lowerBound": "1",
                   "upperBound": "100",
                   "dbtable": table_name,
                   "numPartitions": "2",
                   "partitionColumn": part_col,
                   "user": secret_conf["mysql_conf"]["username"],
                   "password": secret_conf["mysql_conf"]["password"]
                   }
    df = spark \
        .read \
        .format("jdbc") \
        .option("driver", "com.mysql.cj.jdbc.Driver") \
        .options(**jdbc_params) \
        .load()

    return df


def read_from_sftp(spark, app_secret, secret_file, filepath):
    print(f"Loading file from: {filepath}")
    print(f"Host: {app_secret['sftp_conf']['hostname']}")
    print(f"Port: {app_secret['sftp_conf']['port']}")
    print(f"Username: {app_secret['sftp_conf']['username']}")
    print(f"PEM file path: {secret_file}")
    return spark.read \
        .format("com.springml.spark.sftp")\
        .option("host", app_secret["sftp_conf"]["hostname"])\
        .option("port", app_secret["sftp_conf"]["port"])\
        .option("username", app_secret["sftp_conf"]["username"])\
        .option("pem", secret_file)\
        .option("fileType", "csv")\
        .option("delimiter", "|")\
        .load(filepath)




def read_from_s3(spark, path, delimiter='|', header='true'):
    print("\nReading data from S3,")
    df = spark.read \
        .option("header", header) \
        .format("csv") \
        .option("delimiter", delimiter) \
        .load(path)
    return df


def read_from_mongoDB(spark, database,collection):
    print("\nReading data from MongoDB,")
    df = spark.read \
        .format("com.mongodb.spark.sql.DefaultSource") \
        .option("database", database) \
        .option("collection", collection) \
        .load()
    return df

def read_parquet_from_s3(spark,file_path):
    return spark.read \
        .option("header", "true") \
        .option("delimiter", "|") \
        .parquet(file_path)


def write_data_to_Redshift(txn_df,jdbc_url,s3_path,redshift_table_name):
    txn_df.coalesce(1).write \
            .format("io.github.spark_redshift_community.spark.redshift") \
            .option("url", jdbc_url) \
            .option("tempdir", s3_path) \
            .option("forward_spark_s3_credentials", "true") \
            .option("dbtable", redshift_table_name) \
            .mode("overwrite") \
            .save()