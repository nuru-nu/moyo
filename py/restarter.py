"""Restarts programs & reports status."""

import subprocess, sys, time

import network, util

waits_i = 0
waits_secs = [0, 0, 0, 10, 10, 10, 60]
waits_reset_secs = 60

logger = util.createLogger('restarter')

argv = ['python'] + sys.argv[1:]


stats = 'initial'
name = 'restarter_{}'.format(' '.join(argv[1:]))
status_sender = StatusSender(name, logger=logger)

counter = 0
times_log = []
waits_log = []
while True:
    status_sender.send(stats)
    logger.info('starting {}'.format(argv))
    started = time.time()
    subprocess.run(argv)
    stopped = time.time()
    times_log.append(int(stopped - started))
    counter += 1
    if stopped - started > waits_reset_secs:
        waits_i = 0
    wait = waits[waits_i]
    waits_log.append(wait)
    waits_i += 1
    logger.info('stopped, waiting {} seconds'.format(wait))
    time.sleep(wait)
    stats = 'counter={} times_log={} waits_log={}'.format(
        counter, times_log, waits_log
    )