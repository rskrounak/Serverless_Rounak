import atexit
import functools
import logging

import werkzeug.serving

from . import webapi, scheduld, env, operations, datacontext


_logger = logging.getLogger(__name__)


def create():
   
    try:
        env.init()

        _logger.info('ECS Scheduler v%s', env.get_version())
        app = webapi.create()

        try:
            from uwsgidecorators import postfork
            postfork(functools.partial(_setup_application, app))
        except ImportError:
            
            if werkzeug.serving.is_running_from_reloader() or not app.debug:
                _setup_application(app)

        return app
    except Exception:
        _logger.critical('unhandled startup exception', exc_info=True)
        raise


def _setup_application(app):
    ops_queue = operations.DirectQueue()
    jobs_dc = datacontext.Jobs.load()

    _logger.info('Starting scheduld...')
    _launch_scheduld(ops_queue, jobs_dc)

    _logger.info('Setting up webapi...')
    webapi.setup(app, ops_queue, jobs_dc)


def _launch_scheduld(ops_queue, jobs_dc):
    scheduler = scheduld.create(ops_queue, jobs_dc)
    scheduler.start()
    atexit.register(_on_exit, scheduler)


def _on_exit(scheduler):
    scheduler.stop()