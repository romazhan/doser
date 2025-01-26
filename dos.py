from typing import Dict, Tuple, Callable, Awaitable, Any
import multiprocessing as mp
import asyncio, aiohttp
import random, string
import os, gc


def _check_dict_are_mutable(d: Dict[Any, Any]) -> bool:
    for v in d.values():
        if callable(v):
            return True
        elif isinstance(v, dict):
            if _check_dict_are_mutable(v):
                return True

    return False

def _process_mutable_dict(d: Dict[Any, Any]) -> Dict[Any, Any]:
    d_copy = d.copy()

    for k, v in d_copy.items():
        if isinstance(v, dict):
            d_copy[k] = _process_mutable_dict(v)
        elif callable(v):
            d_copy[k] = v()

    return d_copy

class AlwaysRandomValue(object):
    __slots__ = (
        '_length',
        '_chars',
        '_extra_chars',
        '_prefix',
        '_postfix'
    )

    def __init__(
        self,
        length: int | Tuple[int, int],
        chars: str = f'{string.ascii_letters}{string.digits}',
        extra_chars: str = '',
        prefix: str = '',
        postfix: str = ''
    ) -> None:
        self._length = length
        self._chars = chars
        self._extra_chars = extra_chars
        self._prefix = prefix
        self._postfix = postfix

    def __call__(self) -> str:
        length = self._length
        if isinstance(self._length, tuple):
            length = random.randint(*length)

        return self._prefix + ''.join(
            random.choice(f'{self._chars}{self._extra_chars}') for _ in range(length)
        ) + self._postfix

class Doser(object):
    __slots__ = (
        '_process_count',
        '_async_request_count',
        '_request_loop_count',
        '_use_gc_collect',
        '_request_kwargs_are_mutable',
    )

    def __init__(
        self,
        process_count: int = 5,
        async_request_count: int = 50,
        request_loop_count: int = 10 ** 100,
        use_gc_collect: bool = False
    ) -> None:
        self._process_count = process_count
        self._async_request_count = async_request_count
        self._request_loop_count = request_loop_count
        self._use_gc_collect = use_gc_collect

        self._request_kwargs_are_mutable: bool | None = None

    def start(
        self,
        url: str,
        method: str = 'GET',
        timeout_sec: int = 10,
        verify_ssl: bool = False,
        url_format_callback: Callable[[str, int, int], str] | None = None,
        response_callback: Callable[[aiohttp.ClientResponse, int, int], Awaitable[Any]] | None = None,
        http_code_report: bool = True,
        **request_kwargs: Any
    ) -> None:
        self._request_kwargs_are_mutable = _check_dict_are_mutable(request_kwargs)

        try:
            mp.Pool(self._process_count).starmap(
                self._start_event_processing_loop, ((
                    url,
                    method,
                    timeout_sec,
                    verify_ssl,
                    url_format_callback,
                    response_callback,
                    http_code_report,
                    request_kwargs
                ) for _ in range(self._process_count))
            )
        except (KeyboardInterrupt, SystemExit):
            raise

    def _start_event_processing_loop(self, *args: Any) -> None:
        args = list(args)

        request_kwargs = args[-1]
        del args[-1]

        try:
            asyncio.run(self._start_grouped_request_loops(*args, **request_kwargs))
        except KeyboardInterrupt:
            pass

    async def _start_grouped_request_loops(
        self,
        *args: Any,
        **request_kwargs: Any
    ) -> None:
        async with aiohttp.ClientSession() as client:
            await asyncio.gather(*(
                self._start_request_loop(client, *args, **request_kwargs) for _ in range(self._async_request_count)
            ))

    async def _start_request_loop(
        self,
        client: aiohttp.ClientSession,
        url: str,
        method: str,
        timeout_sec: int,
        verify_ssl: bool,
        url_format_callback: Callable[[str, int, int], str] | None,
        response_callback: Callable[[aiohttp.ClientResponse, int, int], Awaitable[Any]] | None,
        http_code_report: bool,
        **request_kwargs: Any
    ) -> None:
        pid = os.getpid()

        for i in range(self._request_loop_count):
            url = url_format_callback(url, i + 1, pid) if callable(url_format_callback) else url

            final_request_kwargs = request_kwargs
            if self._request_kwargs_are_mutable:
                final_request_kwargs = _process_mutable_dict(request_kwargs)

            try:
                async with client.request(
                    method,
                    url,
                    timeout=timeout_sec,
                    ssl=verify_ssl,
                    **final_request_kwargs
                ) as response:
                    http_code_report and print(f'[status_code]: {response.status} ({pid})')

                    callable(response_callback) and await response_callback(response, i + 1, pid)
            except Exception as unknown_e:
                str(unknown_e).strip() and print(f'[error][{pid}]: {unknown_e}')

                self._use_gc_collect and gc.collect()
