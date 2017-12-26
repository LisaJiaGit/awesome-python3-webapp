#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Lisa Jia'

'''
async web application.
'''

import logging; logging.basicConfig(level=logging.INFO)
import asyncio, os, json, time
from datetime import datetime

from aiohttp import web
from jinja2 import Environment, FileSystemLoader
from ipdb import set_trace

import orm
from coroweb import add_routes, add_static
from handlers import cookie2user, COOKIE_NAME
from config import configs


async def logger_factory(app, handler):
    async def logger(request):
        logging.info('Request: %s %s' % (request.method, request.path))
        return (await handler(request))
    return logger 


async def auth_factory(app, handler):
    async def auth(request):
        
        #set_trace()
        logging.info('check user: %s %s' % (request.method, request.path))
        request.__user__ = None
        cookie_str = request.cookies.get(COOKIE_NAME)
        if cookie_str:
            user = await cookie2user(cookie_str)
            if user:
                logging.info('set current user: %s' % user.email)
                request.__user__ = user

        #user must signin before blog edit(localhost:9000/manage/blogs/create)
        if request.path.startswith('/manage/'):
            # 0 / 0 = 0;
            #request.__user__.admin (default is False)            
            if request.__user__ is None or request.__user__.admin:
                logging.info('sign in before create blog.')
                return web.HTTPFound('/signin')
            
        return (await handler(request))
    return auth
        

async def data_factory(app, handler):
    async def parse_data(request):
        if request.method == 'POST':
            if request.content_type.startswith('application/json'):
                request.__data__ = await request.json()
                logging.info('request json: %s' % str(request.__data__))
            elif request.content_type.startswith('application/x-www-form-urlencoded'):
                request.__data__ = await request.post()
                logging.info('request form: %s' % str(request.__data__))
        return (await handler(request))
    return parse_data 


'''
results from handlers
'''
async def response_factory(app, handler):
    async def response(request):
  
        #set_trace()        
        logging.info('Response handler...')
        #call RequestHandler in coroweb.py
        r = await handler(request)

        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp 
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp 
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                #Serialize obj to a JSON formatted str 
                resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                #template = 'test.html'
                #r = 
                #render(): render the template with some variables
                r['__user__'] = request.__user__
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp 
        if isinstance(r, int) and r >= 100 and r < 600:
            return web.Response(r)
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(t, str(m))

        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp
    return response


def init_jinja2(app, **kw):
    logging.info('init jinja2...')
    options = dict(
        autoescape = kw.get('autoescape', True),
        block_start_string = kw.get('block_start_string', '{%'),
        block_end_string = kw.get('block_end_string', '%}'),
        variable_start_string = kw.get('variable_start_string', '{{'),
        variable_end_string = kw.get('variable_end_string', '}}'),
        auto_reload = kw.get('auto_reload', True)
    )
    path = kw.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logging.info('set jinja2 template path: %s' % path)
    #Instances of Environment are used to store the configuration and global objects,
    #and are used to load templates from the file system or other locations. 
    env = Environment(loader=FileSystemLoader(path), **options)
    
    filters = kw.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
            
    #app['__templating__'] used in response_factory
    app['__templating__'] = env 
    

#filter will be used in template("blogs/html") like {{blog.created_at|datetime}} 
#the arg t is blog.created_at
def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return '1 minute ago'
    if delta < 3600:
        return '%s minutes ago' % (delta // 60)
    if delta < 86400:
        return '%s hours ago' % (delta // 3600)
    if delta < 604800:
        return '%s days ago' % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return '%s-%s-%s' % (dt.year, dt.month, dt.day)


'''
Application is a synonym for web-server.
To get fully working example, you have to make application, register supported
urls in router and create a server socket with Server as a protocol factory.
Server could be constructed with Application.make_handler(). 
'''
async def init(loop):
    #make connection to MySQL server on local host to access mysql database
    #so that "index" in handler.py can use User.findAll()  
    #set_trace()
    await orm.create_pool(loop=loop, **configs.db)
    
    #make application and provides a powerful mechanism for customizing request handlers via middlewares.
    #set_trace()    
    app = web.Application(loop=loop, middlewares=[logger_factory, auth_factory,
                                                  data_factory, response_factory])
    
    #create template Environment than get_template in response_factory. 
    #set_trace()    
    init_jinja2(app, filters=dict(datetime=datetime_filter))
    
    #get request.method, request.path and request handle to return response.
    #set_trace()    
    add_routes(app, 'handlers')
    
    #response_factory will handle RequestHandler results(from add_routes) by template.
    
    #set_trace()    
    add_static(app)
    
    #app,.make_handler() is for  creating a server socket with Server as a protocol factory.
    #set_trace()    
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('server started at http://127.0.0.1:9000...')
    return srv 

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
