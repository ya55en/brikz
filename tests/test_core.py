"""Behaviour specs for the `core` module."""

from __future__ import annotations

import dataclasses

import httpx
import pytest
from authlib.integrations.httpx_client import OAuth1Auth

from brikz import __version__
from brikz.core import (
    BASE_URL,
    AsyncBrickLink,
    BrickLink,
    BrickLinkAPIError,
    BrickLinkCredentials,
    BrikzError,
    JsonStruct,
    MalformedResponseError,
    Request,
    clean_params,
    unwrap,
    user_agent,
)


def envelope_transport(
    json_body: dict[str, object], status_code: int = 200
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=json_body, request=request)

    return httpx.MockTransport(handler)


def capturing_transport() -> tuple[httpx.MockTransport, list[httpx.Request]]:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"meta": {"code": 200}, "data": None}, request=request)

    return httpx.MockTransport(handler), captured


def parse_foo(data: JsonStruct | None) -> object:
    assert isinstance(data, dict)
    return data["foo"]


def envelope_response(json_body: dict[str, object], status_code: int = 200) -> httpx.Response:
    request = httpx.Request("GET", "https://api.bricklink.com/api/store/v1/items/SET/1")
    return httpx.Response(status_code, json=json_body, request=request)


CREDENTIALS = BrickLinkCredentials(
    consumer_key="a-consumer-key",
    consumer_secret="a-consumer-secret",
    token="a-token",
    token_secret="a-token-secret",
)


class describe_BrickLinkCredentials:
    def it_names_the_account_in_its_repr(self):
        assert "a-consumer-key" in repr(CREDENTIALS)

    @pytest.mark.parametrize(
        "secret",
        ["a-consumer-secret", "a-token", "a-token-secret"],
    )
    def it_keeps_every_secret_out_of_its_repr(self, secret: str):
        assert secret not in repr(CREDENTIALS)

    def it_refuses_to_be_mutated(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            CREDENTIALS.token = "another-token"  # pyright: ignore[reportAttributeAccessIssue]

    def it_builds_an_auth_flow_httpx_can_use(self):
        assert isinstance(CREDENTIALS.auth(), httpx.Auth)

    def it_hands_all_four_values_to_the_auth_flow(self):
        auth = CREDENTIALS.auth()

        assert isinstance(auth, OAuth1Auth)
        assert auth.client_id == "a-consumer-key"
        assert auth.client_secret == "a-consumer-secret"
        assert auth.token == "a-token"
        assert auth.token_secret == "a-token-secret"

    def it_builds_a_fresh_auth_flow_for_every_client(self):
        assert CREDENTIALS.auth() is not CREDENTIALS.auth()


class describe_BrickLinkAPIError:
    def it_is_a_brikz_error(self):
        assert issubclass(BrickLinkAPIError, BrikzError)

    def it_keeps_the_envelope_fields_reachable(self):
        error = BrickLinkAPIError(code=404, message="RESOURCE_NOT_FOUND", description="")

        assert error.code == 404
        assert error.message == "RESOURCE_NOT_FOUND"
        assert error.description == ""

    def it_reads_as_code_message_and_description(self):
        error = BrickLinkAPIError(
            code=400,
            message="PARAMETER_MISSING_OR_INVALID",
            description="color_id is invalid",
        )

        assert str(error) == "[400] PARAMETER_MISSING_OR_INVALID: color_id is invalid"

    def it_tolerates_an_absent_description(self):
        error = BrickLinkAPIError(code=401, message="BAD_OAUTH_REQUEST")

        assert error.description == ""
        assert str(error) == "[401] BAD_OAUTH_REQUEST: "


class describe_MalformedResponseError:
    def it_is_a_brikz_error(self):
        assert issubclass(MalformedResponseError, BrikzError)

    def it_keeps_the_offending_response_for_inspection(self):
        response = httpx.Response(502, text="<html>Bad Gateway</html>")

        assert MalformedResponseError(response).response is response

    def it_reports_the_status_and_the_body(self):
        response = httpx.Response(502, text="<html>Bad Gateway</html>")

        assert str(MalformedResponseError(response)) == "HTTP 502: '<html>Bad Gateway</html>'"

    def it_shortens_a_long_body_to_200_characters(self):
        response = httpx.Response(500, text="x" * 5000)

        message = str(MalformedResponseError(response))

        assert message == f"HTTP 500: {'x' * 200!r}"


class describe_BrickLink:
    def it_talks_to_the_bricklink_api_by_default(self):
        with BrickLink(CREDENTIALS) as client:
            assert str(client._client.base_url) == BASE_URL + "/"

    def it_accepts_another_base_url(self):
        with BrickLink(CREDENTIALS, base_url="https://example.test") as client:
            assert str(client._client.base_url) == "https://example.test"

    def it_signs_every_request_with_the_credentials(self):
        transport, captured = capturing_transport()

        with BrickLink(CREDENTIALS, transport=transport) as client:
            client.get("/items/SET/1")

        authorization = captured[0].headers["Authorization"]
        assert "a-consumer-key" in authorization

    def it_identifies_itself_with_a_brikz_user_agent(self):
        transport, captured = capturing_transport()

        with BrickLink(CREDENTIALS, transport=transport) as client:
            client.get("/items/SET/1")

        assert captured[0].headers["User-Agent"] == user_agent()

    def it_forwards_extra_keyword_arguments_to_httpx(self):
        with BrickLink(CREDENTIALS, timeout=42) as client:
            assert client._client.timeout.connect == 42

    def it_answers_a_get_with_the_unwrapped_data(self):
        transport = envelope_transport({"meta": {"code": 200}, "data": {"foo": "bar"}})

        with BrickLink(CREDENTIALS, transport=transport) as client:
            assert client.get("/items/SET/1") == {"foo": "bar"}

    def it_lets_an_api_error_escape_get(self):
        transport = envelope_transport(
            {"meta": {"code": 404, "message": "RESOURCE_NOT_FOUND"}}, status_code=404
        )

        with (
            BrickLink(CREDENTIALS, transport=transport) as client,
            pytest.raises(BrickLinkAPIError),
        ):
            client.get("/items/SET/1")

    def it_leaves_unset_query_parameters_out_of_the_request(self):
        transport, captured = capturing_transport()

        with BrickLink(CREDENTIALS, transport=transport) as client:
            client.get("/items/SET/1", params={"color_id": None, "region": "eu"})

        assert "color_id" not in captured[0].url.params
        assert captured[0].url.params["region"] == "eu"

    def it_closes_the_underlying_client(self):
        client = BrickLink(CREDENTIALS)
        client.close()

        assert client._client.is_closed

    def it_closes_itself_on_leaving_a_with_block(self):
        with BrickLink(CREDENTIALS) as client:
            pass

        assert client._client.is_closed


class describe_AsyncBrickLink:
    pytestmark = pytest.mark.anyio

    async def it_talks_to_the_bricklink_api_by_default(self):
        async with AsyncBrickLink(CREDENTIALS) as client:
            assert str(client._client.base_url) == BASE_URL + "/"

    async def it_accepts_another_base_url(self):
        async with AsyncBrickLink(CREDENTIALS, base_url="https://example.test") as client:
            assert str(client._client.base_url) == "https://example.test"

    async def it_signs_every_request_with_the_credentials(self):
        transport, captured = capturing_transport()

        async with AsyncBrickLink(CREDENTIALS, transport=transport) as client:
            await client.get("/items/SET/1")

        authorization = captured[0].headers["Authorization"]
        assert "a-consumer-key" in authorization

    async def it_identifies_itself_with_a_brikz_user_agent(self):
        transport, captured = capturing_transport()

        async with AsyncBrickLink(CREDENTIALS, transport=transport) as client:
            await client.get("/items/SET/1")

        assert captured[0].headers["User-Agent"] == user_agent()

    async def it_forwards_extra_keyword_arguments_to_httpx(self):
        async with AsyncBrickLink(CREDENTIALS, timeout=42) as client:
            assert client._client.timeout.connect == 42

    async def it_answers_a_get_with_the_unwrapped_data(self):
        transport = envelope_transport({"meta": {"code": 200}, "data": {"foo": "bar"}})

        async with AsyncBrickLink(CREDENTIALS, transport=transport) as client:
            assert await client.get("/items/SET/1") == {"foo": "bar"}

    async def it_lets_an_api_error_escape_get(self):
        transport = envelope_transport(
            {"meta": {"code": 404, "message": "RESOURCE_NOT_FOUND"}}, status_code=404
        )

        async with AsyncBrickLink(CREDENTIALS, transport=transport) as client:
            with pytest.raises(BrickLinkAPIError):
                await client.get("/items/SET/1")

    async def it_leaves_unset_query_parameters_out_of_the_request(self):
        transport, captured = capturing_transport()

        async with AsyncBrickLink(CREDENTIALS, transport=transport) as client:
            await client.get("/items/SET/1", params={"color_id": None, "region": "eu"})

        assert "color_id" not in captured[0].url.params
        assert captured[0].url.params["region"] == "eu"

    async def it_closes_the_underlying_client(self):
        client = AsyncBrickLink(CREDENTIALS)
        await client.aclose()

        assert client._client.is_closed

    async def it_closes_itself_on_leaving_an_async_with_block(self):
        async with AsyncBrickLink(CREDENTIALS) as client:
            pass

        assert client._client.is_closed


class describe_Request:
    def it_carries_a_path_and_a_parser(self):
        def parse(data: object) -> object:
            return data

        request = Request(path="/items/SET/1", parse=parse)

        assert request.path == "/items/SET/1"
        assert request.parse is parse

    def it_carries_no_query_parameters_by_default(self):
        request = Request(path="/items/SET/1", parse=lambda data: data)

        assert request.params == {}

    def it_refuses_to_be_mutated(self):
        request = Request(path="/items/SET/1", parse=lambda data: data)

        with pytest.raises(dataclasses.FrozenInstanceError):
            request.path = "/items/SET/2"  # pyright: ignore[reportAttributeAccessIssue]


class describe_BrickLink_send:
    def it_gets_the_path_the_request_names(self):
        transport, captured = capturing_transport()
        request = Request(path="/items/SET/1", parse=lambda data: data)

        with BrickLink(CREDENTIALS, transport=transport) as client:
            client.send(request)

        assert captured[0].url.path == "/api/store/v1/items/SET/1"

    def it_passes_the_query_parameters_the_request_carries(self):
        transport, captured = capturing_transport()
        request = Request(path="/items/SET/1", parse=lambda data: data, params={"color_id": 5})

        with BrickLink(CREDENTIALS, transport=transport) as client:
            client.send(request)

        assert captured[0].url.params["color_id"] == "5"

    def it_answers_with_whatever_the_requests_parser_returns(self):
        transport = envelope_transport({"meta": {"code": 200}, "data": {"foo": "bar"}})
        request = Request(path="/items/SET/1", parse=parse_foo)

        with BrickLink(CREDENTIALS, transport=transport) as client:
            assert client.send(request) == "bar"

    def it_leaves_unset_query_parameters_out_of_the_request(self):
        transport, captured = capturing_transport()
        request = Request(
            path="/items/SET/1",
            parse=lambda data: data,
            params={"color_id": None, "region": "eu"},
        )

        with BrickLink(CREDENTIALS, transport=transport) as client:
            client.send(request)

        assert "color_id" not in captured[0].url.params
        assert captured[0].url.params["region"] == "eu"

    def it_lets_an_api_error_escape(self):
        transport = envelope_transport(
            {"meta": {"code": 404, "message": "RESOURCE_NOT_FOUND"}}, status_code=404
        )
        request = Request(path="/items/SET/1", parse=lambda data: data)

        with (
            BrickLink(CREDENTIALS, transport=transport) as client,
            pytest.raises(BrickLinkAPIError),
        ):
            client.send(request)


class describe_AsyncBrickLink_send:
    pytestmark = pytest.mark.anyio

    async def it_gets_the_path_the_request_names(self):
        transport, captured = capturing_transport()
        request = Request(path="/items/SET/1", parse=lambda data: data)

        async with AsyncBrickLink(CREDENTIALS, transport=transport) as client:
            await client.send(request)

        assert captured[0].url.path == "/api/store/v1/items/SET/1"

    async def it_answers_with_whatever_the_requests_parser_returns(self):
        transport = envelope_transport({"meta": {"code": 200}, "data": {"foo": "bar"}})
        request = Request(path="/items/SET/1", parse=parse_foo)

        async with AsyncBrickLink(CREDENTIALS, transport=transport) as client:
            assert await client.send(request) == "bar"

    async def it_lets_an_api_error_escape(self):
        transport = envelope_transport(
            {"meta": {"code": 404, "message": "RESOURCE_NOT_FOUND"}}, status_code=404
        )
        request = Request(path="/items/SET/1", parse=lambda data: data)

        async with AsyncBrickLink(CREDENTIALS, transport=transport) as client:
            with pytest.raises(BrickLinkAPIError):
                await client.send(request)


class describe_unwrap:
    def it_returns_the_data_of_a_successful_envelope(self):
        response = envelope_response({"meta": {"code": 200}, "data": {"foo": "bar"}})

        assert unwrap(response) == {"foo": "bar"}

    def it_returns_none_when_the_envelope_carries_no_data(self):
        response = envelope_response({"meta": {"code": 200}})

        assert unwrap(response) is None

    def it_raises_an_api_error_on_a_non_2xx_meta_code(self):
        response = envelope_response(
            {"meta": {"code": 404, "message": "RESOURCE_NOT_FOUND"}}, status_code=404
        )

        with pytest.raises(BrickLinkAPIError):
            unwrap(response)

    def it_carries_the_meta_fields_into_the_api_error(self):
        response = envelope_response(
            {
                "meta": {
                    "code": 400,
                    "message": "PARAMETER_MISSING_OR_INVALID",
                    "description": "color_id is invalid",
                }
            },
            status_code=400,
        )

        with pytest.raises(BrickLinkAPIError) as excinfo:
            unwrap(response)

        assert excinfo.value.code == 400
        assert excinfo.value.message == "PARAMETER_MISSING_OR_INVALID"
        assert excinfo.value.description == "color_id is invalid"

    def it_says_n_a_for_meta_fields_the_envelope_omits(self):
        response = envelope_response({"meta": {"code": 401}}, status_code=401)

        with pytest.raises(BrickLinkAPIError) as excinfo:
            unwrap(response)

        assert excinfo.value.message == "n/a"
        assert excinfo.value.description == "n/a"

    def it_reports_the_http_status_when_a_failed_response_has_no_envelope(self):
        request = httpx.Request("GET", "https://api.bricklink.com/api/store/v1/items/SET/1")
        response = httpx.Response(502, text="<html>Bad Gateway</html>", request=request)

        with pytest.raises(httpx.HTTPStatusError):
            unwrap(response)

    def it_reports_a_malformed_response_when_the_body_is_not_json(self):
        request = httpx.Request("GET", "https://api.bricklink.com/api/store/v1/items/SET/1")
        response = httpx.Response(200, text="not json", request=request)

        with pytest.raises(MalformedResponseError):
            unwrap(response)

    def it_reports_a_malformed_response_when_meta_is_missing(self):
        response = envelope_response({"data": {"foo": "bar"}})

        with pytest.raises(MalformedResponseError):
            unwrap(response)

    def it_reports_a_malformed_response_when_data_is_a_scalar(self):
        response = envelope_response({"meta": {"code": 200}, "data": "not-a-dict-or-list"})

        with pytest.raises(MalformedResponseError):
            unwrap(response)

    def it_accepts_a_list_as_data(self):
        response = envelope_response({"meta": {"code": 200}, "data": [1, 2]})

        assert unwrap(response) == [1, 2]

    def it_reports_a_malformed_response_when_the_body_is_a_bare_list(self):
        request = httpx.Request("GET", "https://api.bricklink.com/api/store/v1/items/SET/1")
        response = httpx.Response(200, json=[1, 2, 3], request=request)

        with pytest.raises(MalformedResponseError):
            unwrap(response)

    def it_coerces_a_string_meta_code(self):
        response = envelope_response({"meta": {"code": "200"}, "data": {"foo": "bar"}})

        assert unwrap(response) == {"foo": "bar"}

    def it_reports_a_malformed_response_when_meta_code_is_missing(self):
        response = envelope_response({"meta": {}, "data": {"foo": "bar"}})

        with pytest.raises(MalformedResponseError):
            unwrap(response)

    def it_returns_none_for_a_body_less_204_response(self):
        request = httpx.Request("DELETE", "https://api.bricklink.com/api/store/v1/items/SET/1")
        response = httpx.Response(204, request=request)

        assert unwrap(response) is None

    def it_reports_the_http_status_for_a_body_less_error_response(self):
        request = httpx.Request("DELETE", "https://api.bricklink.com/api/store/v1/items/SET/1")
        response = httpx.Response(500, request=request)

        with pytest.raises(httpx.HTTPStatusError):
            unwrap(response)

    def it_trusts_the_envelope_over_the_http_status(self):
        # A well-formed 2xx envelope on a non-2xx transport status is treated
        # as success: meta.code, not the HTTP status, is the source of truth.
        response = envelope_response({"meta": {"code": 200}, "data": {"a": 1}}, status_code=500)

        assert unwrap(response) == {"a": 1}


class describe_clean_params:
    def it_drops_the_parameters_that_are_unset(self):
        assert clean_params({"a": 1, "b": None}) == {"a": 1}

    def it_keeps_falsy_values_that_are_not_none(self):
        assert clean_params({"a": 0, "b": "", "c": False}) == {"a": 0, "b": "", "c": False}

    def it_yields_an_empty_mapping_when_given_nothing(self):
        assert clean_params(None) == {}


class describe_user_agent:
    def it_reads_the_name_and_version_off_the_package(self):
        assert user_agent() == f"brikz/{__version__}"

    def it_computes_the_string_only_once(self):
        user_agent.cache_clear()
        try:
            first = user_agent()
            assert user_agent() is first  # same object => not recomputed
        finally:
            user_agent.cache_clear()
