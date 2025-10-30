# -*- coding: utf-8 -*-
"""
HTTP 客户端封装
"""
import time
import random
import requests
from typing import Optional, Dict
from urllib.parse import urljoin


class HttpClient:
    """HTTP 客户端，支持重试、延迟等功能"""

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        min_interval: int = 0,
        max_interval: int = 0,
        verify_ssl: bool = True
    ):
        """
        初始化 HTTP 客户端

        Args:
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            min_interval: 最小请求间隔（毫秒）
            max_interval: 最大请求间隔（毫秒）
            verify_ssl: 是否验证 SSL 证书
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.min_interval = min_interval / 1000.0 if min_interval else 0
        self.max_interval = max_interval / 1000.0 if max_interval else 0
        self.verify_ssl = verify_ssl

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def _add_delay(self):
        """添加随机延迟"""
        if self.max_interval > 0:
            delay = random.uniform(self.min_interval, self.max_interval)
            time.sleep(delay)

    def get(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        cookies: Optional[Dict] = None
    ) -> requests.Response:
        """
        发送 GET 请求

        Args:
            url: 请求 URL
            params: 查询参数
            headers: 请求头
            cookies: Cookies

        Returns:
            响应对象
        """
        self._add_delay()

        for attempt in range(self.max_retries):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    cookies=cookies,
                    timeout=self.timeout,
                    verify=self.verify_ssl
                )
                response.raise_for_status()
                return response

            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise
                print(f"请求失败，正在重试 ({attempt + 1}/{self.max_retries}): {e}")
                time.sleep(1 * (attempt + 1))

    def post(
        self,
        url: str,
        data: Optional[Dict] = None,
        json: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        cookies: Optional[Dict] = None
    ) -> requests.Response:
        """
        发送 POST 请求

        Args:
            url: 请求 URL
            data: 表单数据
            json: JSON 数据
            headers: 请求头
            cookies: Cookies

        Returns:
            响应对象
        """
        self._add_delay()

        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    url,
                    data=data,
                    json=json,
                    headers=headers,
                    cookies=cookies,
                    timeout=self.timeout,
                    verify=self.verify_ssl
                )
                response.raise_for_status()
                return response

            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise
                print(f"请求失败，正在重试 ({attempt + 1}/{self.max_retries}): {e}")
                time.sleep(1 * (attempt + 1))

    def close(self):
        """关闭会话"""
        self.session.close()
