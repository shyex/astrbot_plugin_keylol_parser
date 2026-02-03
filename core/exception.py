"""异常定义"""

class ParseException(Exception):
    """解析异常"""
    pass

class RedirectException(ParseException):
    """重定向异常"""
    pass

class DownloadException(Exception):
    """下载异常"""
    pass

class DownloadLimitException(DownloadException):
    """下载限制异常"""
    pass

class SizeLimitException(DownloadException):
    """大小限制异常"""
    pass

class ZeroSizeException(DownloadException):
    """零大小异常"""
    pass
