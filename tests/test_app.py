import random

from aiohttp import ClientResponseError

import aiohttp_retry
from aiohttp_retry import RetryClient, RetryOptions
from tests.app import App


async def test_hello(aiohttp_client, loop):
    test_app = App()
    app = test_app.get_app()

    client = await aiohttp_client(app)
    retry_client = RetryClient()
    retry_client._client = client

    async with retry_client.get('/ping') as response:
        text = await response.text()
        assert response.status == 200
        assert text == 'Ok!'

        assert test_app.counter == 1

    await retry_client.close()
    await client.close()


async def test_hello_with_context(aiohttp_client, loop):
    test_app = App()
    app = test_app.get_app()

    client = await aiohttp_client(app)

    async with RetryClient() as retry_client:
        retry_client._client = client
        async with retry_client.get('/ping') as response:
            text = await response.text()
            assert response.status == 200
            assert text == 'Ok!'

            assert test_app.counter == 1

    await client.close()


async def test_internal_error(aiohttp_client, loop):
    test_app = App()
    app = test_app.get_app()

    client = await aiohttp_client(app)
    retry_client = RetryClient()
    retry_client._client = client

    retry_options = RetryOptions(attempts=5)
    async with retry_client.get('/internal_error', retry_options) as response:
        assert response.status == 500
        assert test_app.counter == 6  # initial attempt + 5 retries

    await retry_client.close()
    await client.close()


async def test_not_found_error(aiohttp_client, loop):
    test_app = App()
    app = test_app.get_app()

    client = await aiohttp_client(app)
    retry_client = RetryClient()
    retry_client._client = client

    retry_options = RetryOptions(attempts=5, statuses={404})
    async with retry_client.get('/not_found_error', retry_options) as response:
        assert response.status == 404
        assert test_app.counter == 6  # initial attempt + 5 retries

    await retry_client.close()
    await client.close()


async def test_sometimes_error(aiohttp_client, loop):
    test_app = App()
    app = test_app.get_app()

    client = await aiohttp_client(app)
    retry_client = RetryClient()
    retry_client._client = client

    retry_options = RetryOptions(attempts=5)
    async with retry_client.get('/sometimes_error', retry_options) as response:
        text = await response.text()
        assert response.status == 200
        assert text == 'Ok!'

        assert test_app.counter == 3

    await retry_client.close()
    await client.close()


async def test_sometimes_error_with_raise_for_status(aiohttp_client, loop):
    test_app = App()
    app = test_app.get_app()

    client = await aiohttp_client(app, raise_for_status=True)
    retry_client = RetryClient()
    retry_client._client = client

    retry_options = RetryOptions(attempts=5, exceptions={ClientResponseError})
    async with retry_client.get('/sometimes_error', retry_options) \
            as response:
        text = await response.text()
        assert response.status == 200
        assert text == 'Ok!'

        assert test_app.counter == 3

    await retry_client.close()
    await client.close()


async def test_override_options(aiohttp_client, loop):
    test_app = App()
    app = test_app.get_app()

    client = await aiohttp_client(app)
    retry_options = RetryOptions(attempts=1)
    retry_client = RetryClient(retry_options=retry_options)
    retry_client._client = client

    retry_options = RetryOptions(attempts=5)
    async with retry_client.get('/sometimes_error', retry_options) as response:
        text = await response.text()
        assert response.status == 200
        assert text == 'Ok!'

        assert test_app.counter == 3

    await retry_client.close()
    await client.close()


async def test_hello_awaitable(aiohttp_client, loop):
    test_app = App()
    app = test_app.get_app()

    client = await aiohttp_client(app)
    retry_client = RetryClient()
    retry_client._client = client

    response = await retry_client.get('/ping')
    text = await response.text()
    assert response.status == 200
    assert text == 'Ok!'

    assert test_app.counter == 1

    await retry_client.close()
    await client.close()


def test_retry_timeout_exponential_backoff():
    retry = aiohttp_retry.ExponentialRetry(attempts=10)
    timeouts = list(retry.timeouts())
    assert timeouts == [10, 0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4, 12.8, 25.6, 51.2]


def test_retry_timeout_random():
    retry = aiohttp_retry.RandomRetry(attempts=10, random=random.Random(0).random)
    timeouts = [round(t, 2) for t in retry.timeouts()]
    assert timeouts == [10, 2.55, 2.3, 1.32, 0.85, 1.58, 1.27, 2.37, 0.98, 1.48, 1.79]
    assert all(retry.min_timeout <= t <= retry.max_timeout for t in timeouts[1:])


def test_retry_timeout_list():
    expected = [10, 1.2, 2.1, 3.4, 4.3, 4.5, 5.4, 5.6, 6.5, 6.7, 7.6]
    retry = aiohttp_retry.ListRetry(expected[1:])
    timeouts = list(retry.timeouts())
    assert timeouts == expected
