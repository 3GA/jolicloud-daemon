#!/usr/bin/env python

__author__ = 'Jeremy Bethmont'

import gio
import os

from datetime import datetime

from twisted.internet import reactor, protocol

from jolicloud_daemon.plugins import LinuxSessionManager
from jolicloud_daemon.enums import *

class FilesystemManager(LinuxSessionManager):
    
    _infos = 'standard::type,standard::size,standard::content-type,time::modified'
    
    def list_(self, request, handler, path='/', root='home'):
        
        if root == 'home' or root == 'HOME':
            root = os.getenv('HOME')
        
        def format_path(f):
            if len(root) and f.startswith(root):
                return f[len(root):]
            return f
        
        def info_cb(file, result):
            try:
                info = file.query_info_finish(result)
                result = {
                    'path': format_path(file.get_path()),
                    'modified': datetime.fromtimestamp(info.get_modification_time()).strftime('%a, %d %b %Y %H:%M:%S %Z'),
                    'mime_type': info.get_content_type(),
                    'thumbnail': False,
                }
                if info.get_file_type() == gio.FILE_TYPE_DIRECTORY:
                    result['is_dir'] = True
                    result['bytes'] = 0
                    result['contents'] = []
                    def get_contents(c_file, c_result):
                        c_infos = c_file.enumerate_children_finish(c_result)
                        for c_info in c_infos:
                            name = c_info.get_name()
                            path = c_file.get_child(name).get_path()
                            if not name.startswith('.'):
                                result['contents'].append({
                                    'path': format_path(path),
                                    'modified': datetime.fromtimestamp(c_info.get_modification_time()).strftime('%a, %d %b %Y %H:%M:%S %Z'),
                                    'is_dir': c_info.get_file_type() == gio.FILE_TYPE_DIRECTORY,
                                    'bytes': c_info.get_size(),
                                    'mime_type': c_info.get_content_type(),
                                    'thumbnail': False,
                                })
                        handler.send_data(request, result)
                        handler.success(request)
                    file.enumerate_children_async('standard::name,%s' % self._infos, callback=get_contents)
                else:
                    result['is_dir'] = False
                    result['bytes'] = info.get_size()
                    handler.send_data(request, result)
                    handler.success(request)
            except gio.Error, e: # Path does not exist?
                handler.failed(request)
        print '%s/%s' % (root, path.strip('/'))
        current = gio.File('%s/%s' % (root, path.strip('/')))
        current.query_info_async(self._infos, callback=info_cb)
        
    def open_(self, request, handler, path='/', root='home'):
        
        if root == 'home' or root == 'HOME':
            root = os.getenv('HOME')
        
        f = reactor.spawnProcess(
            protocol.ProcessProtocol(),
            '/usr/bin/setsid', # setsid - run a program in a new session
            ['setsid', 'xdg-open', '%s/%s' % (root, path.strip('/'))],
            env=os.environ
        )
        handler.success(request)
            
        
filesystemManager = FilesystemManager()
