import logging
import platform
from importlib.metadata import version

import allure
import lxml.builder
import pytest
from lxml import etree
from playwright.sync_api import Playwright

logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    """Pytest method for adding custom console parameters."""
    parser.addoption("--ci", action="store_true", default=False, help="Launch test in the remote browser if provided")
    parser.addoption("--testid", action="store", metavar="test id", help="only run tests with specified test ids")


def pytest_configure(config):
    """Pytest hook to register additional marker."""
    config.addinivalue_line("markers", "testid(name): run only tests with specified test ids")


def pytest_runtest_setup(item):
    passed_option = item.config.getoption("--testid")
    if passed_option:
        passed_option = passed_option.split(",")
    testids = [mark.args[0] for mark in item.iter_markers(name="testid")]
    test_id = ""
    if testids:
        test_id = testids[0]
    if passed_option and test_id not in passed_option:
        pytest.skip(f"Specified test id not in {testids!r}")


# @pytest.hookimpl(hookwrapper=True)
# def pytest_runtest_makereport(item):
#     outcome = yield
#     rep = outcome.get_result()
#     setattr(item, "rep_" + rep.when, rep)
#     return rep


@pytest.fixture(scope="session", autouse=True)
@allure.title("Create Environment widget")
def allure_environment(request):
    """Creating xml file for Environment widget in Allure report."""
    allure_dir = request.config.getoption("--alluredir")
    # TODO: add the base url to the report
    if allure_dir is not None:
        e = lxml.builder.ElementMaker()
        environment = e.environment
        parameter = e.parameter
        key = e.key
        value = e.value
        the_doc = environment(
            parameter(key("Python version"), value(platform.python_version())),
            parameter(key("OS platform"), value(platform.system())),
            parameter(key("Machine"), value(platform.machine())),
        )
        with open(allure_dir + "/environment.xml", "wb") as file:
            file.write(etree.tostring(the_doc, pretty_print=True))


@pytest.fixture(scope="session")
@allure.title("Setup the browser")
def browser_setup(request, browser_name, playwright: Playwright, browser_type_launch_args):
    if request.config.getoption("--ci"):
        playwright_version = version("playwright")
        logger.info(f"Connecting to the remote browser {browser_name} by playwright version {playwright_version}")
        browser = playwright.__getattribute__(browser_name).connect(
            ws_endpoint=f"ws://remote_host/playwright/{browser_name}/playwright-{playwright_version}?"
            f"headless=false&enableVNC=true&enableVideo=false",
            timeout=60000,
        )
    else:
        logger.info(f"Starting the local {browser_name} browser")
        browser = playwright.__getattribute__(browser_name).launch(**browser_type_launch_args)
    yield browser
    if browser:
        logger.info("Closing the browser")
        browser.close()


@pytest.fixture(scope="function")
@allure.title("Set up the regular page")
def page_setup(browser_setup, browser_context_args):
    context = browser_setup.new_context(**browser_context_args)
    page = context.new_page()
    logger.info("Successfully initiated the new page with a standard context")
    yield page
    page.close()
    context.close()
    logger.info("Successfully closed the page with a standard context")
