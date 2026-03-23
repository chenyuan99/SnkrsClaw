"""
Unit tests for main.py – SnkrsClaw Nike SNKRS bot.

All Selenium WebDriver interactions are mocked so tests run without a browser.
The `pause` package is unavailable on Python 3.11 so it is stubbed out before
importing main; _sleep_until() (the in-module replacement) is also patched.
"""
import json
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Stub out 'pause' before importing main (can't build on Python 3.11)
# ---------------------------------------------------------------------------
_pause_stub = types.ModuleType("pause")
_pause_stub.until = MagicMock()
sys.modules.setdefault("pause", _pause_stub)

import main  # noqa: E402  (import after stub)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_driver():
    """Return a MagicMock that behaves like a Selenium WebDriver."""
    driver = MagicMock()
    driver.page_source = "<html></html>"
    return driver


def _make_element(text="10", css_class="active"):
    """Return a MagicMock WebElement."""
    el = MagicMock()
    el.text = text
    el.get_attribute.return_value = css_class
    return el


# ===========================================================================
# _sleep_until
# ===========================================================================

class TestSleepUntil(unittest.TestCase):

    @patch("main.time")
    def test_sleeps_for_future_datetime(self, mock_time):
        from datetime import datetime, timezone, timedelta
        future = datetime.now(tz=timezone.utc) + timedelta(seconds=5)
        main._sleep_until(future)
        mock_time.sleep.assert_called_once()
        sleep_arg = mock_time.sleep.call_args[0][0]
        self.assertGreater(sleep_arg, 0)
        self.assertLessEqual(sleep_arg, 5.1)

    @patch("main.time")
    def test_no_sleep_for_past_datetime(self, mock_time):
        from datetime import datetime, timezone, timedelta
        past = datetime.now(tz=timezone.utc) - timedelta(seconds=10)
        main._sleep_until(past)
        mock_time.sleep.assert_not_called()


# ===========================================================================
# wait_until_* helpers
# ===========================================================================

class TestWaitHelpers(unittest.TestCase):

    def setUp(self):
        self.driver = _make_driver()

    @patch("main.WebDriverWait")
    def test_wait_until_visible_xpath(self, mock_wdw):
        main.wait_until_visible(self.driver, xpath="//div", duration=5)
        mock_wdw.assert_called_once_with(self.driver, 5, 0.01)
        mock_wdw.return_value.until.assert_called_once()

    @patch("main.WebDriverWait")
    def test_wait_until_visible_class_name(self, mock_wdw):
        main.wait_until_visible(self.driver, class_name="foo", duration=5)
        mock_wdw.assert_called_once_with(self.driver, 5, 0.01)

    @patch("main.WebDriverWait")
    def test_wait_until_visible_id(self, mock_wdw):
        main.wait_until_visible(self.driver, el_id="myId", duration=5)
        mock_wdw.assert_called_once_with(self.driver, 5, 0.01)

    @patch("main.WebDriverWait")
    def test_wait_until_visible_no_locator_noop(self, mock_wdw):
        main.wait_until_visible(self.driver)
        mock_wdw.assert_not_called()

    @patch("main.WebDriverWait")
    def test_wait_until_clickable_xpath(self, mock_wdw):
        main.wait_until_clickable(self.driver, xpath="//button", duration=5)
        mock_wdw.assert_called_once_with(self.driver, 5, 0.01)

    @patch("main.WebDriverWait")
    def test_wait_until_clickable_no_locator_noop(self, mock_wdw):
        main.wait_until_clickable(self.driver)
        mock_wdw.assert_not_called()

    @patch("main.WebDriverWait")
    def test_wait_until_present_returns_element(self, mock_wdw):
        sentinel = object()
        mock_wdw.return_value.until.return_value = sentinel
        result = main.wait_until_present(self.driver, xpath="//span", duration=5)
        self.assertIs(result, sentinel)

    @patch("main.WebDriverWait")
    def test_wait_until_present_id_returns_element(self, mock_wdw):
        sentinel = object()
        mock_wdw.return_value.until.return_value = sentinel
        result = main.wait_until_present(self.driver, el_id="someId", duration=5)
        self.assertIs(result, sentinel)

    @patch("main.WebDriverWait")
    def test_wait_until_present_no_locator_returns_none(self, mock_wdw):
        result = main.wait_until_present(self.driver)
        self.assertIsNone(result)
        mock_wdw.assert_not_called()


# ===========================================================================
# select_shoe_size
# ===========================================================================

class TestSelectShoeSize(unittest.TestCase):

    def setUp(self):
        self.driver = _make_driver()

    @patch("main.wait_until_visible")
    def test_skip_size_selection_no_click(self, mock_wait):
        main.select_shoe_size(self.driver, shoe_size="10", shoe_type="M", skip_size_selection=True)
        self.driver.find_element_by_xpath.assert_not_called()

    @patch("main.wait_until_visible")
    def test_numeric_size_uses_exact_text(self, mock_wait):
        size_el = _make_element(text="10")   # no letters → numeric branch
        container_el = _make_element()
        self.driver.find_element_by_xpath.side_effect = [size_el, container_el]
        container_el.find_element_by_xpath.return_value = _make_element()

        main.select_shoe_size(self.driver, shoe_size="10", shoe_type="M", skip_size_selection=False)
        container_el.find_element_by_xpath.assert_called_once()
        xpath_arg = container_el.find_element_by_xpath.call_args[0][0]
        self.assertIn("10", xpath_arg)

    @patch("main.wait_until_visible")
    def test_alpha_size_M_type_format(self, mock_wait):
        size_el = _make_element(text="M 10")
        container_el = _make_element()
        self.driver.find_element_by_xpath.side_effect = [size_el, container_el]
        container_el.find_element_by_xpath.return_value = _make_element()

        main.select_shoe_size(self.driver, shoe_size="10", shoe_type="M", skip_size_selection=False)
        xpath_arg = container_el.find_element_by_xpath.call_args[0][0]
        self.assertIn("M 10", xpath_arg)

    @patch("main.wait_until_visible")
    def test_alpha_size_Y_type_concatenates(self, mock_wait):
        """Kids 'Y' type: shoe_size + shoe_type → '10Y'."""
        size_el = _make_element(text="10Y")
        container_el = _make_element()
        self.driver.find_element_by_xpath.side_effect = [size_el, container_el]
        container_el.find_element_by_xpath.return_value = _make_element()

        main.select_shoe_size(self.driver, shoe_size="10", shoe_type="Y", skip_size_selection=False)
        xpath_arg = container_el.find_element_by_xpath.call_args[0][0]
        self.assertIn("10Y", xpath_arg)

    @patch("main.wait_until_visible")
    def test_special_shoe_type_XL(self, mock_wait):
        """Special type XL with no size uses exact button text."""
        size_el = _make_element(text="XL")
        container_el = _make_element()
        self.driver.find_element_by_xpath.side_effect = [size_el, container_el]
        container_el.find_element_by_xpath.return_value = _make_element()

        main.select_shoe_size(self.driver, shoe_size=None, shoe_type="XL", skip_size_selection=False)
        xpath_arg = container_el.find_element_by_xpath.call_args[0][0]
        self.assertIn("XL", xpath_arg)


# ===========================================================================
# click_buy_button
# ===========================================================================

class TestClickBuyButton(unittest.TestCase):

    @patch("main.wait_until_present")
    def test_executes_script_click(self, mock_present):
        driver = _make_driver()
        el = _make_element()
        mock_present.return_value = el
        main.click_buy_button(driver)
        driver.execute_script.assert_called_once_with("arguments[0].click();", el)


# ===========================================================================
# select_shipping_option
# ===========================================================================

class TestSelectShippingOption(unittest.TestCase):

    @patch("main.wait_until_present")
    def test_standard_does_nothing(self, mock_present):
        driver = _make_driver()
        main.select_shipping_option(driver, "STANDARD")
        mock_present.assert_not_called()
        driver.execute_script.assert_not_called()

    @patch("main.wait_until_present")
    def test_two_day_clicks_element(self, mock_present):
        driver = _make_driver()
        el = _make_element()
        mock_present.return_value = el
        main.select_shipping_option(driver, "TWO_DAY")
        mock_present.assert_called_once_with(driver, el_id="TWO_DAY", duration=10)
        driver.execute_script.assert_called_once_with("arguments[0].click();", el)

    @patch("main.wait_until_present")
    def test_next_day_clicks_element(self, mock_present):
        driver = _make_driver()
        el = _make_element()
        mock_present.return_value = el
        main.select_shipping_option(driver, "NEXT_DAY")
        mock_present.assert_called_once_with(driver, el_id="NEXT_DAY", duration=10)


# ===========================================================================
# input_address
# ===========================================================================

class TestInputAddress(unittest.TestCase):

    def _sample_address(self):
        return {
            "first_name": "John",
            "last_name": "Doe",
            "address": "123 Main St",
            "apt": "Apt 4",
            "city": "Portland",
            "state": "OR",
            "zip_code": "97201",
            "phone_number": "5031234567",
        }

    @patch("main.wait_until_visible")
    def test_fills_all_eight_fields(self, mock_wait):
        driver = _make_driver()
        field = _make_element()
        driver.find_element_by_id.return_value = field

        main.input_address(driver, self._sample_address())

        self.assertEqual(driver.find_element_by_id.call_count, 8)
        self.assertEqual(field.clear.call_count, 8)
        self.assertEqual(field.send_keys.call_count, 8)

    @patch("main.wait_until_visible")
    def test_correct_field_order(self, mock_wait):
        driver = _make_driver()
        fields = [_make_element() for _ in range(8)]
        driver.find_element_by_id.side_effect = fields

        main.input_address(driver, self._sample_address())

        sent = [f.send_keys.call_args[0][0] for f in fields]
        self.assertEqual(sent, [
            "John", "Doe", "123 Main St", "Apt 4",
            "Portland", "OR", "97201", "5031234567",
        ])


# ===========================================================================
# click_save_button
# ===========================================================================

class TestClickSaveButton(unittest.TestCase):

    @patch("main.wait_until_clickable")
    @patch("main.wait_until_present")
    @patch("main.WebDriverWait")
    def test_default_xpath_save_and_continue(self, mock_wdw, mock_present, mock_clickable):
        driver = _make_driver()
        el = _make_element(css_class="btn-active")
        mock_present.return_value = el
        mock_wdw.return_value.until.side_effect = lambda fn: fn(driver)

        main.click_save_button(driver)

        driver.find_element_by_xpath.assert_called_once()
        xpath_arg = driver.find_element_by_xpath.call_args[0][0]
        self.assertIn("Save & Continue", xpath_arg)

    @patch("main.wait_until_clickable")
    @patch("main.wait_until_present")
    @patch("main.WebDriverWait")
    def test_custom_xpath_forwarded(self, mock_wdw, mock_present, mock_clickable):
        driver = _make_driver()
        mock_present.return_value = _make_element()
        mock_wdw.return_value.until.side_effect = lambda fn: fn(driver)
        custom = "//button[@id='myBtn']"

        main.click_save_button(driver, xpath_o=custom)

        mock_present.assert_called_once_with(driver, xpath=custom, duration=10)

    @patch("main.wait_until_clickable")
    @patch("main.wait_until_present")
    def test_check_disabled_false_skips_webdriverwait(self, mock_present, mock_clickable):
        driver = _make_driver()
        mock_present.return_value = _make_element()

        with patch("main.WebDriverWait") as mock_wdw:
            main.click_save_button(driver, check_disabled=False)
            mock_wdw.assert_not_called()


# ===========================================================================
# click_add_new_address_button
# ===========================================================================

class TestClickAddNewAddressButton(unittest.TestCase):

    @patch("main.wait_until_clickable")
    def test_clicks_correct_xpath(self, _):
        driver = _make_driver()
        main.click_add_new_address_button(driver)
        driver.find_element_by_xpath.assert_called_once()
        self.assertIn("Add New Address", driver.find_element_by_xpath.call_args[0][0])


# ===========================================================================
# click_submit_button
# ===========================================================================

class TestClickSubmitButton(unittest.TestCase):

    @patch("main.wait_until_clickable")
    @patch("main.wait_until_present")
    @patch("main.WebDriverWait")
    def test_default_submit_order_xpath(self, mock_wdw, mock_present, mock_clickable):
        driver = _make_driver()
        mock_present.return_value = _make_element()
        mock_wdw.return_value.until.side_effect = lambda fn: fn(driver)

        main.click_submit_button(driver)

        driver.find_element_by_xpath.assert_called_once()
        self.assertIn("Submit Order", driver.find_element_by_xpath.call_args[0][0])

    @patch("main.wait_until_clickable")
    @patch("main.wait_until_present")
    @patch("main.WebDriverWait")
    def test_custom_xpath_used(self, mock_wdw, mock_present, mock_clickable):
        driver = _make_driver()
        mock_present.return_value = _make_element()
        mock_wdw.return_value.until.side_effect = lambda fn: fn(driver)
        custom = "//button[@id='submitBtn']"

        main.click_submit_button(driver, xpath_o=custom)

        mock_present.assert_called_once_with(driver, xpath=custom, duration=10)


# ===========================================================================
# poll_checkout_phase_one
# ===========================================================================

class TestPollCheckoutPhaseOne(unittest.TestCase):

    @patch("main.check_add_new_address_button")
    def test_address_button_visible_all_skip_false(self, mock_check):
        mock_check.return_value = None
        skip_addr, skip_ship, skip_pay = main.poll_checkout_phase_one(_make_driver())
        self.assertFalse(skip_addr)
        self.assertFalse(skip_ship)
        self.assertFalse(skip_pay)

    @patch("main.check_shipping")
    @patch("main.check_add_new_address_button", side_effect=Exception("not found"))
    def test_shipping_visible_skips_address(self, _addr, mock_ship):
        mock_ship.return_value = None
        skip_addr, skip_ship, skip_pay = main.poll_checkout_phase_one(_make_driver())
        self.assertTrue(skip_addr)
        self.assertFalse(skip_ship)
        self.assertFalse(skip_pay)

    @patch("main.check_payment")
    @patch("main.check_shipping", side_effect=Exception("not found"))
    @patch("main.check_add_new_address_button", side_effect=Exception("not found"))
    def test_payment_visible_skips_address_and_shipping(self, _a, _s, mock_pay):
        mock_pay.return_value = None
        skip_addr, skip_ship, skip_pay = main.poll_checkout_phase_one(_make_driver())
        self.assertTrue(skip_addr)
        self.assertTrue(skip_ship)
        self.assertFalse(skip_pay)

    @patch("main.check_submit_button")
    @patch("main.check_payment", side_effect=Exception("not found"))
    @patch("main.check_shipping", side_effect=Exception("not found"))
    @patch("main.check_add_new_address_button", side_effect=Exception("not found"))
    def test_submit_visible_skips_all(self, _a, _s, _p, mock_submit):
        mock_submit.return_value = None
        skip_addr, skip_ship, skip_pay = main.poll_checkout_phase_one(_make_driver())
        self.assertTrue(skip_addr)
        self.assertTrue(skip_ship)
        self.assertTrue(skip_pay)


# ===========================================================================
# poll_checkout_phase_two
# ===========================================================================

class TestPollCheckoutPhaseTwo(unittest.TestCase):

    @patch("main.check_payment")
    def test_payment_visible_returns_false(self, mock_pay):
        mock_pay.return_value = None
        self.assertFalse(main.poll_checkout_phase_two(_make_driver()))

    @patch("main.check_submit_button")
    @patch("main.check_payment", side_effect=Exception("not found"))
    def test_submit_visible_skips_payment(self, _pay, mock_submit):
        mock_submit.return_value = None
        self.assertTrue(main.poll_checkout_phase_two(_make_driver()))


# ===========================================================================
# login
# ===========================================================================

class TestLogin(unittest.TestCase):

    @patch("main.wait_until_visible")
    def test_successful_login_flow(self, mock_wait):
        driver = _make_driver()
        el = _make_element()
        driver.find_element_by_xpath.return_value = el

        main.login(driver, "user@example.com", "secret")

        driver.get.assert_called_once_with(main.NIKE_HOME_URL)
        driver.find_element_by_xpath.assert_called()

    @patch("main.wait_until_visible")
    def test_login_timeout_on_get_is_swallowed(self, mock_wait):
        from selenium.common.exceptions import TimeoutException
        driver = _make_driver()
        driver.get.side_effect = TimeoutException("timeout")
        driver.find_element_by_xpath.return_value = _make_element()

        # Should NOT raise
        main.login(driver, "user@example.com", "secret")
        driver.find_element_by_xpath.assert_called()


# ===========================================================================
# run() – high-level orchestration
# ===========================================================================

class TestRun(unittest.TestCase):
    """Tests for run() using mocked dependencies."""

    def _base_patches(self, phase_one=(True, True, True), phase_two=True):
        return [
            patch("main.login"),
            patch("main.select_shoe_size"),
            patch("main.click_buy_button"),
            patch("main.poll_checkout_phase_one", return_value=phase_one),
            patch("main.poll_checkout_phase_two", return_value=phase_two),
        ]

    def test_no_purchase_flag_skips_submit_button(self):
        driver = _make_driver()
        patches = self._base_patches()
        [p.start() for p in patches]
        try:
            with patch("main.click_submit_button") as mock_submit:
                main.run(
                    driver=driver, shoe_type="M", username="u", password="p",
                    url="https://www.nike.com/launch/t/shoe?size=10",
                    shoe_size="10", shipping_option="STANDARD",
                    page_load_timeout=2, purchase=False,
                )
                mock_submit.assert_not_called()
        finally:
            for p in patches:
                p.stop()

    def test_purchase_flag_calls_submit_button(self):
        driver = _make_driver()
        patches = self._base_patches()
        [p.start() for p in patches]
        try:
            with patch("main.click_submit_button") as mock_submit, \
                 patch("main.click_save_button"):
                main.run(
                    driver=driver, shoe_type="M", username="u", password="p",
                    url="https://www.nike.com/launch/t/shoe?size=10",
                    shoe_size="10", shipping_option="STANDARD",
                    page_load_timeout=2, purchase=True,
                )
                mock_submit.assert_called_once()
        finally:
            for p in patches:
                p.stop()

    def test_screenshot_saved_when_path_given(self):
        driver = _make_driver()
        patches = self._base_patches()
        [p.start() for p in patches]
        try:
            main.run(
                driver=driver, shoe_type="M", username="u", password="p",
                url="https://www.nike.com/launch/t/shoe?size=10",
                shoe_size="10", shipping_option="STANDARD",
                page_load_timeout=2, screenshot_path="/tmp/shot.png",
            )
            driver.save_screenshot.assert_called_once_with("/tmp/shot.png")
        finally:
            for p in patches:
                p.stop()

    def test_html_written_when_path_given(self):
        driver = _make_driver()
        driver.page_source = "<html>test</html>"
        patches = self._base_patches()
        [p.start() for p in patches]
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
                html_path = f.name
            main.run(
                driver=driver, shoe_type="M", username="u", password="p",
                url="https://www.nike.com/launch/t/shoe?size=10",
                shoe_size="10", shipping_option="STANDARD",
                page_load_timeout=2, html_path=html_path,
            )
            with open(html_path) as f:
                self.assertEqual(f.read(), "<html>test</html>")
        finally:
            for p in patches:
                p.stop()
            os.unlink(html_path)

    def test_retry_on_buy_button_failure(self):
        """Exceptions that propagate to the outer handler retry up to num_retries times."""
        driver = _make_driver()
        count = {"n": 0}

        def failing_buy(**kwargs):
            count["n"] += 1
            raise Exception("buy fail")

        with patch("main.login"), \
             patch("main.select_shoe_size"), \
             patch("main.click_buy_button", side_effect=failing_buy):
            main.run(
                driver=driver, shoe_type="M", username="u", password="p",
                url="https://www.nike.com/launch/t/shoe",
                shoe_size="10", shipping_option="STANDARD",
                page_load_timeout=2, num_retries=2,
            )
        # initial attempt + 2 retries = 3 total
        self.assertEqual(count["n"], 3)

    def test_login_time_calls_sleep_until(self):
        driver = _make_driver()
        patches = self._base_patches()
        [p.start() for p in patches]
        try:
            with patch("main._sleep_until") as mock_sleep:
                main.run(
                    driver=driver, shoe_type="M", username="u", password="p",
                    url="https://www.nike.com/launch/t/shoe?size=10",
                    shoe_size="10", shipping_option="STANDARD",
                    page_load_timeout=2, login_time="2026-04-01 09:00:00",
                )
                mock_sleep.assert_called_once()
        finally:
            for p in patches:
                p.stop()

    def test_release_time_calls_sleep_until(self):
        driver = _make_driver()
        patches = self._base_patches()
        [p.start() for p in patches]
        try:
            with patch("main._sleep_until") as mock_sleep:
                main.run(
                    driver=driver, shoe_type="M", username="u", password="p",
                    url="https://www.nike.com/launch/t/shoe?size=10",
                    shoe_size="10", shipping_option="STANDARD",
                    page_load_timeout=2, release_time="2026-04-01 10:00:00",
                )
                mock_sleep.assert_called_once()
        finally:
            for p in patches:
                p.stop()

    def test_driver_quit_always_called(self):
        driver = _make_driver()
        patches = self._base_patches()
        [p.start() for p in patches]
        try:
            main.run(
                driver=driver, shoe_type="M", username="u", password="p",
                url="https://www.nike.com/launch/t/shoe?size=10",
                shoe_size="10", shipping_option="STANDARD",
                page_load_timeout=2,
            )
            driver.quit.assert_called_once()
        finally:
            for p in patches:
                p.stop()

    def test_size_in_url_sets_skip_flag(self):
        """When 'size=' is in the URL, select_shoe_size receives skip_size_selection=True."""
        driver = _make_driver()
        patches = self._base_patches()
        mocks = [p.start() for p in patches]
        select_size_mock = mocks[1]
        try:
            main.run(
                driver=driver, shoe_type="M", username="u", password="p",
                url="https://www.nike.com/launch/t/shoe?size=10",
                shoe_size="10", shipping_option="STANDARD",
                page_load_timeout=2,
            )
            kw = select_size_mock.call_args[1]
            self.assertTrue(kw["skip_size_selection"])
        finally:
            for p in patches:
                p.stop()

    def test_no_size_in_url_clears_skip_flag(self):
        driver = _make_driver()
        patches = self._base_patches()
        mocks = [p.start() for p in patches]
        select_size_mock = mocks[1]
        try:
            main.run(
                driver=driver, shoe_type="M", username="u", password="p",
                url="https://www.nike.com/launch/t/shoe",
                shoe_size="10", shipping_option="STANDARD",
                page_load_timeout=2,
            )
            kw = select_size_mock.call_args[1]
            self.assertFalse(kw["skip_size_selection"])
        finally:
            for p in patches:
                p.stop()


# ===========================================================================
# Module-level constants
# ===========================================================================

class TestConstants(unittest.TestCase):

    def test_nike_home_url(self):
        self.assertEqual(main.NIKE_HOME_URL, "https://www.nike.com/login")

    def test_submit_button_xpath_non_empty(self):
        self.assertIsInstance(main.SUBMIT_BUTTON_XPATH, str)
        self.assertTrue(len(main.SUBMIT_BUTTON_XPATH) > 0)

    def test_logger_is_logger_instance(self):
        import logging
        self.assertIsInstance(main.LOGGER, logging.Logger)


# ===========================================================================
# Dependency import smoke tests
# ===========================================================================

class TestDependencyImports(unittest.TestCase):

    def test_selenium_importable(self):
        import selenium
        self.assertIsNotNone(selenium.__version__)

    def test_selenium_version_meets_minimum(self):
        import selenium
        major = int(selenium.__version__.split(".")[0])
        self.assertGreaterEqual(major, 3)

    def test_dateutil_importable(self):
        from dateutil import parser
        dt = parser.parse("2026-04-01 10:00:00")
        self.assertIsNotNone(dt)

    def test_six_importable(self):
        import six
        self.assertIsNotNone(six.__version__)

    def test_webdriver_wait_importable(self):
        from selenium.webdriver.support.ui import WebDriverWait
        self.assertTrue(callable(WebDriverWait))

    def test_expected_conditions_importable(self):
        from selenium.webdriver.support import expected_conditions as EC
        self.assertTrue(callable(EC.element_to_be_clickable))

    def test_by_locators_available(self):
        from selenium.webdriver.common.by import By
        for attr in ("XPATH", "ID", "CSS_SELECTOR", "CLASS_NAME"):
            self.assertTrue(hasattr(By, attr))


if __name__ == "__main__":
    unittest.main()
