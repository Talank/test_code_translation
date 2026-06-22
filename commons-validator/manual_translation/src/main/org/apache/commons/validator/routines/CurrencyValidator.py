from __future__ import annotations
import locale
import re
import decimal
import numbers
import io
import typing
from typing import *
from src.main.org.apache.commons.validator.routines.AbstractNumberValidator import *
from src.main.org.apache.commons.validator.routines.BigDecimalValidator import *


class CurrencyValidator(BigDecimalValidator):

    __CURRENCY_SYMBOL: str = "\u00A4"
    __VALIDATOR: CurrencyValidator = None
    __serialVersionUID: int = -4201640771171486514

    @staticmethod
    def initialize_fields() -> None:
        CurrencyValidator.__VALIDATOR: CurrencyValidator = (
            CurrencyValidator.CurrencyValidator1()
        )

    def _parse(self, value: str, formatter: typing.Any, locale_: typing.Any) -> typing.Any:

        saved_locale = locale.setlocale(locale.LC_ALL, None)
        parsedValue = super()._parse(value, formatter, locale_)
        if parsedValue is not None or not isinstance(formatter, str):
            return parsedValue

        effective_locale = locale_ if locale_ is not None else saved_locale
        try:
            locale.setlocale(locale.LC_ALL, effective_locale)
            currency_symbol = locale.currency(0, symbol=True, grouping=False)[0]
        except locale.Error:
            return parsedValue
        if value and currency_symbol in value:
            parsedValue = value.replace(currency_symbol, "")
        return parsedValue

    @staticmethod
    def CurrencyValidator1() -> CurrencyValidator:
        return CurrencyValidator(True, True)

    def __init__(self, strict: bool, allowFractions: bool) -> None:
        super().__init__(strict, self.CURRENCY_FORMAT, allowFractions)

    @staticmethod
    def getInstance() -> BigDecimalValidator:
        return CurrencyValidator.__VALIDATOR


CurrencyValidator.initialize_fields()
