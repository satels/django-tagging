"""spawning_child.py
"""

from eventlet import api, coros, util, wsgi
util.wrap_socket_with_coroutine_socket()
util.wrap_pipes_with_coroutine_pipes()
util.wrap_threading_local_with_coro_local()

import optparse, os, signal, socket, sys, time

from paste.deploy import loadwsgi

from spawning import reloader_dev


class ExitChild(Exception):
    pass


def read_pipe_and_die(the_pipe, server_coro):
    os.read(the_pipe, 1)
    api.switch(server_coro, exc=ExitChild)


def serve_from_child(sock, base_dir, config_url):
    wsgi_application = loadwsgi.loadapp(config_url, relative_to=base_dir)

    host, port = sock.getsockname()
    print "(%s) wsgi server listening on %s:%s using %s from %s (in %s)" % (
        os.getpid(), host, port, wsgi_application, config_url, base_dir)

    server_event = coros.event()
    try:
        wsgi.server(
            sock, wsgi_application, server_event=server_event)
    except KeyboardInterrupt:
        pass
    except ExitChild:
        pass

    server = server_event.wait()

    last_outstanding = None
    while server.outstanding_requests:
        if last_outstanding != server.outstanding_requests:
            print "(%s) %s requests remaining, waiting..." % (
                os.getpid(), server.outstanding_requests)
        last_outstanding = server.outstanding_requests
        api.sleep(0.1)
    print "(%s) Child exiting: all requests completed at %s" % (
        os.getpid(), time.asctime())


def main():
    parser = optparse.OptionParser()
    parser.add_option("-d", "--dev",
        action='store_true', dest='dev',
        help='If --dev is passed, reload the server any time '
        'a loaded module changes. Otherwise, only when the svn '
        'revision of the current directory changes.')

    options, args = parser.parse_args()

    if len(args) < 5:
        print "Usage: %s controller_pid config_url base_dir httpd_fd death_fd" % (
            sys.argv[0], )
        sys.exit(1)

    controller_pid, config_url, base_dir, httpd_fd, death_fd = args
    controller_pid = int(controller_pid)

    ## Set up the reloader
    if options.dev:
        api.spawn(
            reloader_dev.watch_forever, [], controller_pid, 1)

    ## The parent will catch sigint and tell us to shut down
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    api.spawn(read_pipe_and_die, int(death_fd), api.getcurrent())

    sock = socket.fromfd(int(httpd_fd), socket.AF_INET, socket.SOCK_STREAM)
    serve_from_child(
        sock, base_dir, config_url)


if __name__ == '__main__':
    main()