# -*- coding: utf-8 -*-

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import sys
import os
import hashlib
import time
import json
import re

__addon__               = xbmcaddon.Addon()
__addon_id__            = __addon__.getAddonInfo('id')
__addonname__           = __addon__.getAddonInfo('name')
__datapath__            = xbmc.translatePath(os.path.join('special://profile/addon_data/', __addon_id__)).replace('\\', '/')
__lang__                = __addon__.getLocalizedString

import debug
import bar
import sendRequest
import art
import syncVideo
import syncImage

def start(self):
    # check if exists addon data folder
    if xbmcvfs.exists(__datapath__ + '/') == 0:
        xbmcvfs.mkdir(__datapath__ )
        
    # open settings if frist run
    if xbmcvfs.exists(__datapath__ + '/settings.xml') == 0:
        __addon__.openSettings()
        
    # if start from porgram section by user force sync all data
    try:
        mode = str(sys.argv[1])
    except:
        self.forcedStart = True
        debug.debug('=== FORCED START ===')
    else:
        self.forcedStart = False
    
    self.setXBMC = {}
    self.setXBMC['URL']      = __addon__.getSetting('url')
    self.setXBMC['Token']    = __addon__.getSetting('token')
    self.setXBMC['Notify']   = __addon__.getSetting('notify')
    self.setXBMC['Debug']    = __addon__.getSetting('debug')
    self.setXBMC['Auth']      = __addon__.getSetting('auth')
    self.setXBMC['AuthLogin'] = __addon__.getSetting('authLogin')
    self.setXBMC['AuthPass']  = __addon__.getSetting('authPass')
    
    self.versionWebScript = '2.8.0'
    
    self.progBar = bar.Bar()
    
    # debug settings
    for n, s in self.setXBMC.items():
        debug.debug('XBMC: ' + n + ': ' + s)
    
    # notify if debugging is on
    if 'true' in self.setXBMC['Debug']:
        debug.notify(__lang__(32115).encode('utf-8'))
    
    # prepare URL
    if self.setXBMC['URL'][-1:] != '/':
        self.setXBMC['URL'] = self.setXBMC['URL'] + '/'
    if self.setXBMC['URL'][:7] != 'http://':
        self.setXBMC['URL'] = 'http://' + self.setXBMC['URL']
        
    self.setXBMC['RootURL'] = self.setXBMC['URL'] + 'api/'    
    
    check(self)

# check connection
def check(self):
    
    # get settings
    self.setSITE = sendRequest.getSettings(self)
    if self.setSITE is False:
        debug.notify(__lang__(32100).encode('utf-8'))
        return False
    if len(self.setSITE) > 0:
        for n, s in self.setSITE.items():
            debug.debug('Server: ' + n + ': ' + s)
    
    # post_max_size in bytes
    post_l = self.setSITE['POST_MAX_SIZE'].strip()[:-1]
    post_r = self.setSITE['POST_MAX_SIZE'].strip().lower()[-1:]
    v = { 'g': 3, 'm': 2, 'k': 1 }
    if post_r in v.keys():
        self.setSITE['POST_MAX_SIZE_B'] = int(post_l) * 1024 ** int(v[post_r])
    else:
        self.setSITE['POST_MAX_SIZE_B'] = int(post_l + post_r)
    debug.debug('Server: POST_MAX_SIZE_B: ' + str(self.setSITE['POST_MAX_SIZE_B']))
    
    # check master mode
    if self.setSITE['xbmc_master'] == '1':
        isMaster = xbmc.getCondVisibility('System.IsMaster')
        if isMaster == 0:
            return False
    
    # check token
    if hashlib.md5(self.setXBMC['Token']).hexdigest() != self.setSITE['token_md5']:
        debug.notify(__lang__(32101).encode('utf-8'))
        debug.debug('Wrong Token')
        return False
    else:
        debug.debug('Token is valid')
    
    # get hash tables from site
    self.hashSITE = sendRequest.getHashes(self)
    if self.hashSITE is False:
        return False
        
    # reset hash if forced start
    if self.forcedStart == True:
        for t in self.hashSITE:
            self.hashSITE[t] = ""
    debug.debug('[hashSITE]: ' + str(self.hashSITE))
    
    self.lang = { 'movies': 32201, 'tvshows': 32202, 'episodes': 32203, 'poster': 32117, 'fanart': 32118, 'thumb': 32119, 'exthumb': 32120, 'actors': 32110 }
    
    self.panels = ['actor', 'genre', 'country', 'studio', 'director']
    
    self.tn = {
        'movies': 
        {
            'json': '{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["cast", "title", "plot", "rating", "year", "art", "runtime", "genre", "director", "originaltitle", "country", "set", "imdbnumber", "studio", "trailer", "playcount", "lastplayed", "dateadded", "streamdetails", "file"]}, "id": "1"}',
            'values' : ['id', 'table', 'title', 'originaltitle', 'year', 'rating', 'plot', 'set', 'imdbid', 'studio[]', 'genre[]', 'actor[]', 'runtime', 'country[]', 'director[]', 'trailer', 'file', 'last_played', 'play_count', 'date_added', 'stream[]', 'hash']
        },
        'tvshows':
        {
            'json': '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "originaltitle", "plot", "genre", "cast", "art", "rating", "premiered", "playcount", "lastplayed", "dateadded"]}, "id": 1}',
            'values' : ['id', 'table', 'title', 'originaltitle', 'rating', 'plot', 'genre[]', 'actor[]', 'premiered', 'last_played', 'play_count', 'date_added', 'hash']
        },
        'episodes':
        {
            'json': '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"properties": ["title", "plot", "episode", "season", "tvshowid", "art", "file", "firstaired", "playcount", "lastplayed", "dateadded", "streamdetails"]}, "id": 1}',
            'values' : ['id', 'table', 'title', 'plot', 'episode', 'season', 'tvshow', 'firstaired', 'last_played', 'play_count', 'date_added', 'file', 'stream[]', 'hash']
        }
    }
    
    # check source
    jsonGetSource = '{"jsonrpc": "2.0", "method": "Files.GetSources", "params": {"media": "video"}, "id": 1}'
    jsonGetSource = xbmc.executeJSONRPC(jsonGetSource)
    jsonGetSource = unicode(jsonGetSource, 'utf-8', errors='ignore')
    jsonGetSourceResponse = json.loads(jsonGetSource)
    
    if 'result' in jsonGetSourceResponse and 'sources' in jsonGetSourceResponse['result']:
        for s in jsonGetSourceResponse['result']['sources']:
            if xbmcvfs.exists(s['file']) == 0:
                debug.notify(__lang__(32123).encode('utf-8') + ': ' + s['file'].encode('utf-8'))
                debug.debug('Source inaccessible: ' + s['file'].encode('utf-8'))
                return False
    
    # get videos from XBMC
    dataSORT                            = {}
    dataSORT['videos']                  = ['movies'] ##Only movies for now, 'tvshows', 'episodes']
    
    dataSORT['images']                  = ['movies', 'tvshows', 'episodes', 'actors']
    dataSORT['movies']                  = ['poster', 'fanart', 'exthumb']
    #dataSORT['tvshows']                 = ['poster', 'fanart']
    #dataSORT['episodes']                = ['poster']
    dataSORT['actors']                  = ['thumb']
    
    dataXBMC = getDataFromXBMC(self, dataSORT)
    
    # sync videos
    debug.debug('=== SYNC VIDEOS ===')
    self.cleanNeeded = False
    self.imageNeeded = False
    if syncVideo.sync(self, dataXBMC['videos'], dataSORT['videos']) is False:
        return False
    
    # sync images
    ## DISABLE IMAGES FOR NOW
    ##debug.debug('=== SYNC IMAGES ===')
    ##syncImage.sync(self, dataXBMC['images'], dataSORT)
    
    # send webserver settings
#    if self.setSITE['xbmc_auto_conf_remote'] == '1':
#        debug.debug('=== SYNC WEBSERVER SETTINGS ===')
#        conf_remote = ['services.webserver', 'services.webserverport', 'services.webserverusername', 'services.webserverpassword']
#        send_conf = {}
#        for s in conf_remote:
#            jsonGet = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.GetSettingValue", "params":{"setting": "' + s + '"},"id":1}')
#            jsonGet = unicode(jsonGet, 'utf-8', errors='ignore')
#            jsonGetResponse = json.loads(jsonGet)
#            send_conf[s.replace('services.', '')] = jsonGetResponse['result']['value']
#        if send_conf['webserver'] == False:
#            debug.notify(__lang__(32122).encode('utf-8'))
#            debug.debug('Webserver is disabled')
#        else:
#            sendRequest.send(self, 'autoconfremote', send_conf)
    
    # start generate banner
 #   debug.debug('=== GENREATE BANNER ===')
 #   sendRequest.send(self, 'generatebanner', {'banner': ''})
    
    # start clean database
    if self.cleanNeeded is True:
        debug.debug('=== CLEAN DATABASE ===')
#FIX LATER        sendRequest.send(self, 'cleandb', {'clean': ''})
    
def getDataFromXBMC(self, dataSORT):
    
    dataXBMC                            = {}
    dataXBMC['videos']                  = { 'movies': {}, 'tvshows': {}, 'episodes': {} }
    
    dataXBMC['images']                  = { 'movies': {}, 'tvshows': {}, 'episodes': {}, 'actors': {} }
    dataXBMC['images']['movies']        = { 'poster': {}, 'fanart': {}, 'exthumb': {} }
    dataXBMC['images']['tvshows']       = { 'poster': {}, 'fanart': {} }
    dataXBMC['images']['episodes']      = { 'poster': {} }
    dataXBMC['images']['actors']        = { 'thumb': {} }
    
    self.namesXBMC = { 'movies': {}, 'tvshows': {}, 'episodes': {}, 'actors': {}, 'exthumb': {} }
    
    self.progBar.create(__lang__(32200), __addonname__ + ', ' + __lang__(32206) + '...')
    p = 0
    
    for table in dataSORT['videos']:
        
        p += 33
        self.progBar.update(p, __lang__(32206) + ' - ' + __lang__(self.lang[table]))
        
        jsonGetData = xbmc.executeJSONRPC(self.tn[table]['json'])
        jsonGetData = unicode(jsonGetData, 'utf-8', errors='ignore')
        jsonGetDataResponse = json.loads(jsonGetData)
        
        # prepare array
        dataXBMC['videos'][table] = {}
        if 'result' in jsonGetDataResponse and table in jsonGetDataResponse['result']:
            for data in jsonGetDataResponse['result'][table]:
                
                # prepare array for videos
                dataXBMC['videos'][table][str(data[table[0:-1]+'id'])] = data
                self.namesXBMC[table][data[table[0:-1]+'id']] = data['title']
                
                # prepare array for images
                if 'art' in data:
                    if 'poster' in data['art'] and data['art']['poster'] != '':
                        dataXBMC['images'][table]['poster'][data[table[0:-1]+'id']] = data['art']['poster']
                    else:
                        if 'thumb' in data['art'] and data['art']['thumb'] != '':
                            dataXBMC['images'][table]['poster'][data[table[0:-1]+'id']] = data['art']['thumb']
                    if 'fanart' in data['art'] and data['art']['fanart'] != '' and 'fanart' in dataXBMC['images'][table]:
                        dataXBMC['images'][table]['fanart'][data[table[0:-1]+'id']] = data['art']['fanart']
                if 'cast' in data:
                    for actor in data['cast']:
                        if 'thumbnail' in actor:
                            hash = hashlib.md5(actor['name'].encode('utf-8')).hexdigest()[0:10]
                            dataXBMC['images']['actors']['thumb'][hash] = actor['thumbnail']
                            self.namesXBMC['actors'][hash] = actor['name']
                if 'file' in data:
                    extrathumbs_path = os.path.dirname(data['file'].replace('\\', '/')) + '/extrathumbs/'
                    if xbmcvfs.exists(extrathumbs_path):
                        ex_dir = xbmcvfs.listdir(extrathumbs_path)
                        for thumb in ex_dir[1]:
                            m = re.search('thumb([0-9]).jpg', thumb)
                            if m and 'exthumb' in dataXBMC['images'][table]:
                                id = str(data[table[0:-1]+'id']) + '_t' + m.group(1)
                                dataXBMC['images'][table]['exthumb'][id] = extrathumbs_path + thumb
                                self.namesXBMC[table][id] = data['title']
    
    self.progBar.close()
    
    # debug
    for t, v in dataXBMC.items():
        for type, val in v.items():
            debug.debug('[' + t + type.title() + 'XBMC]: ' + str(val))
    
    return dataXBMC
    