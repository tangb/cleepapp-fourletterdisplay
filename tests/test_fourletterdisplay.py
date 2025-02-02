#!/usr/bin/env python
# -*- coding: utf-8 -*-
from cleep.libs.tests import session, lib
import unittest
import logging
import sys
import time
from datetime import datetime

sys.path.append("../")
from backend.fourletterdisplay import Fourletterdisplay
from backend.fourletterphatdriver import FourLetterPHatDriver
from cleep.exception import (
    InvalidParameter,
    MissingParameter,
    CommandError,
    Unauthorized,
)
from cleep.profiles.alarmprofile import AlarmProfile
from unittest.mock import Mock, patch, call
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()

mock_importlib = Mock()
mock_lib = Mock()
mock_importlib.import_module.return_value = mock_lib


@patch("backend.fourletterdisplay.importlib", mock_importlib)
@patch("backend.fourletterdisplay.FOUR_LETTER_PHAT", mock_lib)
class TestsFourletterdisplay(unittest.TestCase):
    def setUp(self):
        self.session = session.TestSession(self)
        logging.basicConfig(
            level=LOG_LEVEL,
            format=u"%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s",
        )

    def tearDown(self):
        self.session.clean()
        mock_lib.reset_mock()
        mock_importlib.reset_mock()

    def init_session(self, start=True, mock_on_start=True, mock_on_stop=True):
        self.module = self.session.setup(Fourletterdisplay, mock_on_start=mock_on_start, mock_on_stop=mock_on_stop)
        get_time_command = self.session.make_mock_command(
            "get_time", {"hour": 12, "minute": 12}, False, False
        )
        self.session.add_mock_command(get_time_command)

        if start:
            self.session.start_module(self.module)

        # set driver is installed by default
        self.module.driver = Mock()
        self.module.driver.is_installed.return_value = True

    @patch("backend.fourletterdisplay.datetime")
    def test_on_start(self, mock_datetime):
        mock_datetime.now.return_value = datetime(2022, 12, 18, 7, 6, 22, 0)
        self.init_session(mock_on_start=False)
        self.module._get_config_field = Mock()

        self.module._on_start()

        self.module._get_config_field.assert_any_call("currentbrightness")
        mock_lib.print_str.assert_called_with("0706")
        mock_lib.set_decimal.assert_any_call(1, True)

    def test_on_stop(self):
        self.init_session(mock_on_stop=False)
        self.module.clear = Mock()

        self.module.stop()
        time.sleep(1.5)

        self.module.clear.assert_called()

    def test_on_stop_exception(self):
        self.init_session()
        self.module.clear = Mock(side_effect=Exception("Test exception"))

        try:
            self.module.stop()
            time.sleep(1.5)
        except:
            self.fail("Should not raise exception during _configure call")

    def test_on_event_sunrise_nightmode_enabled(self):
        self.init_session()
        nightmode = True
        brightness = 10
        self.module._get_config_field = Mock(side_effect=[nightmode, brightness])
        self.module.change_brightness = Mock()

        self.module.on_event(
            {
                "event": "test.time.sunrise",
            }
        )

        mock_lib.set_brightness.assert_called_with(brightness)

    def test_on_event_sunrise_nightmode_disabled(self):
        self.init_session()
        nightmode = False
        brightness = 10
        self.module._get_config_field = Mock(side_effect=[nightmode, brightness])
        self.module.change_brightness = Mock()

        self.module.on_event(
            {
                "event": "test.time.sunrise",
            }
        )

        self.assertFalse(self.module.change_brightness.called)

    def test_on_event_sunset_nightmode_enabled(self):
        self.init_session()
        nightmode = True
        nightbrightness = 0
        self.module._get_config_field = Mock(side_effect=[nightmode, nightbrightness])

        self.module.on_event(
            {
                "event": "test.time.sunset",
            }
        )

        mock_lib.set_brightness.assert_called_with(nightbrightness)

    def test_on_event_sunset_nightmode_disabled(self):
        self.init_session()
        nightmode = False
        nightbrightness = 10
        self.module._get_config_field = Mock(side_effect=[nightmode, nightbrightness])
        self.module.change_brightness = Mock()

        self.module.on_event(
            {
                "event": "test.time.sunset",
            }
        )

        self.assertFalse(self.module.change_brightness.called)

    def test_on_render_message_profile(self):
        self.init_session()
        self.module.display_message = Mock()
        self.module.set_dots = Mock()
        message = "Hello"

        self.module.on_render("MessageProfile", {"message": message})

        self.module.display_message.assert_called_with(message)
        self.module.set_dots.assert_called_with(middle_left=True)

    def test_on_render_alarm_profile_scheduled(self):
        self.init_session()
        self.module.display_message = Mock()
        self.module.set_dots = Mock()
        message = "Hello"

        self.module.on_render(
            "AlarmProfile", {"status": AlarmProfile.STATUS_SCHEDULED, "count": 1}
        )

        self.module.set_dots.assert_called_with(most_right=True)

    def test_on_render_alarm_profile_unscheduled_without_other_alarm_sheduled(self):
        self.init_session()
        self.module.display_message = Mock()
        self.module.set_dots = Mock()
        message = "Hello"

        self.module.on_render(
            "AlarmProfile", {"status": AlarmProfile.STATUS_UNSCHEDULED, "count": 0}
        )

        self.module.set_dots.assert_called_with(most_right=False)

    def test_on_render_alarm_profile_unscheduled_with_other_alarm_scheduled(self):
        self.init_session()
        self.module.display_message = Mock()
        self.module.set_dots = Mock()
        message = "Hello"

        self.module.on_render(
            "AlarmProfile", {"status": AlarmProfile.STATUS_UNSCHEDULED, "count": 1}
        )

        self.module.set_dots.assert_called_with(most_right=True)

    def test_on_render_unsupported_profile(self):
        self.init_session()
        self.module.display_message = Mock()
        self.module.set_dots = Mock()
        message = "Hello"

        self.module.on_render("InvalidProfile", {"message": message})

        self.assertFalse(self.module.display_message.called)
        self.assertFalse(self.module.set_dots.called)

    def test_import_lib(self):
        self.init_session(False, mock_on_start=False)
        self.module.driver = Mock()
        self.module.driver.is_installed.return_value = True

        self.session.start_module(self.module)
        mock_importlib.import_module.assert_called_with("fourletterphat")

    def test_import_lib_driver_not_installed(self):
        self.init_session(False)
        self.module.driver = Mock()
        self.module.driver.is_installed.return_value = False
        self.session.start_module(self.module)

        with self.assertRaises(Exception) as cm:
            self.module._Fourletterdisplay__import_lib()
        self.assertEqual(str(cm.exception), "Four-letter pHAT driver is not installed")

    def test_import_lib_display_not_connected(self):
        self.init_session(False)
        self.module.driver = Mock()
        self.module.driver.is_installed.return_value = True
        self.session.start_module(self.module)

        mock_importlib.import_module.side_effect = Exception("Test exception")
        with self.assertRaises(Exception) as cm:
            self.module._Fourletterdisplay__import_lib()
        self.assertEqual(
            str(cm.exception),
            "Four-letter pHAT does not seem connected. Please check hardware",
        )

        # restore mock old state
        mock_importlib.import_module.side_effect = None
        mock_importlib.import_module.return_value = mock_lib

    def test_enable_night_mode_enabled_during_day(self):
        self.init_session()
        self.module._set_config_field = Mock()
        self.module._get_config_field = Mock(return_value=6)
        self.module.set_brightness = Mock()
        self.module.is_night_mode = False

        self.module.enable_night_mode(True)

        self.module._set_config_field.assert_any_call("nightmode", True)
        self.module._set_config_field.assert_any_call("currentbrightness", 6)
        self.module._get_config_field.assert_called_with("brightness")
        mock_lib.set_brightness.assert_called_with(6)

    def test_enable_night_mode_enabled_during_night(self):
        self.init_session()
        self.module._set_config_field = Mock()
        self.module._get_config_field = Mock(return_value=6)
        self.module.set_brightness = Mock()
        self.module.is_night_mode = True

        self.module.enable_night_mode(True)

        self.module._set_config_field.assert_any_call("nightmode", True)
        self.module._set_config_field.assert_any_call("currentbrightness", 6)
        self.module._get_config_field.assert_any_call("nightbrightness")
        mock_lib.set_brightness.assert_called_with(6)

    def test_enable_night_mode_disabled_during_day(self):
        self.init_session()
        self.module._set_config_field = Mock()
        self.module._get_config_field = Mock(return_value=6)
        self.module.set_brightness = Mock()
        self.module.is_night_mode = False

        self.module.enable_night_mode(False)

        self.module._set_config_field.assert_any_call("nightmode", False)
        self.module._set_config_field.assert_any_call("currentbrightness", 6)
        self.module._get_config_field.assert_called_with("brightness")
        mock_lib.set_brightness.assert_called_with(6)

    def test_enable_night_mode_disabled_during_night(self):
        self.init_session()
        self.module._set_config_field = Mock()
        self.module._get_config_field = Mock(return_value=6)
        self.module.set_brightness = Mock()
        self.module.is_night_mode = True

        self.module.enable_night_mode(False)

        self.module._set_config_field.assert_any_call("nightmode", False)
        self.module._set_config_field.assert_any_call("currentbrightness", 6)
        self.module._get_config_field.assert_called_with("brightness")
        mock_lib.set_brightness.assert_called_with(6)

    def test_enable_night_mode_invalid_params(self):
        self.init_session()

        with self.assertRaises(MissingParameter) as cm:
            self.module.enable_night_mode(None)
        self.assertEqual(str(cm.exception), 'Parameter "enable" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.enable_night_mode("test")
        self.assertEqual(str(cm.exception), 'Parameter "enable" must be of type "bool"')

    def test_set_night_mode_brightness_during_day(self):
        self.init_session()
        self.module.is_night_mode = False
        self.module._set_config_field = Mock()

        self.module.set_night_mode_brightness(12)

        self.module._set_config_field.assert_called_with("nightbrightness", 12)
        self.assertFalse(mock_lib.set_brightness.called)

    def test_set_night_mode_brightness_during_night(self):
        self.init_session()
        self.module.is_night_mode = True
        self.module._set_config_field = Mock()

        self.module.set_night_mode_brightness(2)

        self.module._set_config_field.assert_any_call("nightbrightness", 2)
        self.module._set_config_field.assert_any_call("currentbrightness", 2)
        mock_lib.set_brightness.assert_called_with(2)

    def test_set_night_mode_brightness_invalid_params(self):
        self.init_session()

        with self.assertRaises(MissingParameter) as cm:
            self.module.set_night_mode_brightness(None)
        self.assertEqual(str(cm.exception), 'Parameter "brightness" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_night_mode_brightness("helo")
        self.assertEqual(
            str(cm.exception), 'Parameter "brightness" must be of type "int"'
        )

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_night_mode_brightness(20)
        self.assertEqual(
            str(cm.exception), 'Parameter "brightness" must be between 0..15'
        )

    def test_clear(self):
        self.init_session()

        self.module.clear()

        mock_lib.clear.assert_called()
        mock_lib.show.assert_called()

    def test_display_message(self):
        self.init_session()

        self.module.display_message("helo")

        mock_lib.print_str.assert_called_with("helo")

    def test_set_brightness_during_day(self):
        self.init_session()
        self.module.is_night_mode = False
        self.module._set_config_field = Mock()

        self.module.set_brightness(12)

        self.module._set_config_field.assert_any_call("brightness", 12)
        self.module._set_config_field.assert_any_call("currentbrightness", 12)
        mock_lib.set_brightness.assert_called_with(12)

    def test_set_brightness_during_night(self):
        self.init_session()
        self.module.is_night_mode = True
        self.module._set_config_field = Mock()

        self.module.set_brightness(2)

        self.module._set_config_field.assert_called_with("brightness", 2)
        self.assertFalse(mock_lib.set_brightness.called)

    def test_set_brightness_invalid_params(self):
        self.init_session()

        with self.assertRaises(MissingParameter) as cm:
            self.module.set_brightness(None)
        self.assertEqual(str(cm.exception), 'Parameter "brightness" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_brightness("helo")
        self.assertEqual(
            str(cm.exception), 'Parameter "brightness" must be of type "int"'
        )

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_brightness(20)
        self.assertEqual(
            str(cm.exception), 'Parameter "brightness" must be between 0..15'
        )

    def test_set_dots(self):
        self.init_session()

        self.module.set_dots(True, False, True, False)

        mock_lib.set_decimal.assert_has_calls(
            [call(0, True), call(1, False), call(2, True), call(3, False)]
        )
        mock_lib.show.assert_called()


class TestsFourLetterPHatDriver(unittest.TestCase):
    def setUp(self):
        self.lib = lib.TestLib()
        logging.basicConfig(
            level=LOG_LEVEL,
            format=u"%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s",
        )

    def tearDown(self):
        pass

    def init_session(self):
        self.fs = Mock()
        self.driver = FourLetterPHatDriver()
        self.driver.cleep_filesystem = Mock()
        self.driver._on_registered()

    @patch("backend.fourletterphatdriver.ConfigTxt")
    @patch("backend.fourletterphatdriver.EtcModules")
    def test_install(self, mock_etcmodules, mock_configtxt):
        self.init_session()

        self.driver._install(None)

        mock_configtxt.return_value.enable_i2c.assert_called()
        mock_etcmodules.return_value.enable_module.assert_called_with("i2c-dev")

    @patch("backend.fourletterphatdriver.ConfigTxt")
    @patch("backend.fourletterphatdriver.EtcModules")
    def test_uninstall(self, mock_etcmodules, mock_configtxt):
        self.init_session()

        try:
            self.driver._uninstall()
        except:
            self.fail("Uninstall should not fail")

        self.assertFalse(mock_configtxt.return_value.enable_i2c.called)
        self.assertFalse(mock_etcmodules.return_value.enable_module.called)

    @patch("backend.fourletterphatdriver.ConfigTxt")
    @patch("backend.fourletterphatdriver.EtcModules")
    def test_is_installed_installed(self, mock_etcmodules, mock_configtxt):
        self.init_session()
        mock_configtxt.return_value.is_i2c_enabled.return_value = True
        mock_etcmodules.return_value.is_module_enabled.return_value = True

        self.assertTrue(self.driver.is_installed())

    @patch("backend.fourletterphatdriver.ConfigTxt")
    @patch("backend.fourletterphatdriver.EtcModules")
    def test_is_installed_not_installed(self, mock_etcmodules, mock_configtxt):
        self.init_session()

        mock_configtxt.return_value.is_i2c_enabled.return_value = False
        mock_etcmodules.return_value.is_module_enabled.return_value = True
        self.assertFalse(self.driver.is_installed())

        mock_configtxt.return_value.is_i2c_enabled.return_value = True
        mock_etcmodules.return_value.is_module_enabled.return_value = False
        self.assertFalse(self.driver.is_installed())

        mock_configtxt.return_value.is_i2c_enabled.return_value = False
        mock_etcmodules.return_value.is_module_enabled.return_value = False
        self.assertFalse(self.driver.is_installed())


if __name__ == "__main__":
    # coverage run --omit="*lib/python*/*","test_*" --concurrency=thread test_fourletterdisplay.py; coverage report -m -i
    unittest.main()
