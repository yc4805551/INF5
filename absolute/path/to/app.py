@app.cli.command("")
def ingest_command():
    ingest_data()
    click.echo("数据导入过程完成。")