"""Repository 层：所有 SQL 都在这个包里，一个文件对应一张（或一组）表。

这里只负责读写数据，不判断业务规则；规则在 services 和 workflow.py 里。
"""
