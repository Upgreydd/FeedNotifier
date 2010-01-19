import wx
import wx.lib.iewin as ie
import webbrowser
import templates

BLANK = 'about:blank'
COMMAND_CLOSE = 'feednotifier://close/'
COMMAND_NEXT = 'feednotifier://next/'
COMMAND_PREVIOUS = 'feednotifier://previous/'
COMMAND_FIRST = 'feednotifier://first/'
COMMAND_LAST = 'feednotifier://last/'
COMMAND_PLAY = 'feednotifier://play/'
COMMAND_PAUSE = 'feednotifier://pause/'

class Event(wx.PyEvent):
    def __init__(self, event_object, type):
        super(Event, self).__init__()
        self.SetEventType(type.typeId)
        self.SetEventObject(event_object)
        
EVT_LINK = wx.PyEventBinder(wx.NewEventType())
EVT_POPUP_CLOSE = wx.PyEventBinder(wx.NewEventType())

class BrowserControl(ie.IEHtmlWindow):
    def __init__(self, parent):
        super(BrowserControl, self).__init__(parent, -1)
    def update_size(self):
        try:
            body = self.ctrl.Document.body
            width = body.scrollWidth
            height = body.scrollHeight
            self.SetSize((width, height))
        except AttributeError:
            pass
    def BeforeNavigate2(self, *args):
        event = Event(self, EVT_LINK)
        event.link = args[1][0]
        self.ProcessEvent(event)
        return not event.GetSkipped()
        
class PopupFrame(wx.Frame):
    def __init__(self):
        style = wx.STAY_ON_TOP | wx.FRAME_NO_TASKBAR | wx.BORDER_NONE
        title = 'Feed Notifier'
        super(PopupFrame, self).__init__(None, -1, title, style=style)
        self.SetTransparent(230)
        self.control = BrowserControl(self)
    def load_src(self, html):
        control = self.control
        control.LoadString(html)
        control.update_size()
        self.Fit()
        x, y, w, h = wx.ClientDisplayRect()
        cw, ch = self.GetSize()
        x = x + w - cw - 10
        y = y + h - ch - 10
        self.SetPosition((x, y))
        
class PopupManager(wx.EvtHandler):
    def __init__(self):
        super(PopupManager, self).__init__()
        self.timer = None
        self.auto = True
        self.cache = {}
    def set_items(self, items, index=0):
        self.clear_cache()
        self.items = list(items)
        self.index = index
        self.count = len(self.items)
        self.update()
        self.set_timer()
    def update(self):
        item = self.items[self.index]
        if item in self.cache:
            self.show_frame()
            self.update_cache()
        else:
            self.update_cache()
            self.show_frame()
    def update_cache(self):
        indexes = set()
        #indexes.add(0)
        indexes.add(self.index - 1)
        indexes.add(self.index)
        indexes.add(self.index + 1)
        #indexes.add(self.count - 1)
        items = set(self.items[index] for index in indexes if index >= 0 and index < self.count)
        for item in items:
            if item in self.cache:
                continue
            frame = self.create_frame(item)
            self.cache[item] = frame
        for item, frame in self.cache.items():
            if item not in items:
                frame.Close()
                del self.cache[item]
    def clear_cache(self):
        for item, frame in self.cache.items():
            frame.Close()
            del self.cache[item]
    def show_frame(self):
        current_item = self.items[self.index]
        current_item.read = True
        for item, frame in self.cache.items():
            if item == current_item:
                frame.Disable()
                frame.Show()
                frame.Enable()
                frame.Update()
        for item, frame in self.cache.items():
            if item != current_item:
                frame.Hide()
    def create_frame(self, item):
        html = self.render_item(item)
        frame = PopupFrame()
        frame.control.Bind(EVT_LINK, self.on_link)
        frame.load_src(html)
        return frame
    def render_item(self, item):
        context = {}
        count = str(self.count)
        index = str(self.items.index(item) + 1)
        index = '%s%s' % ('0' * (len(count) - len(index)), index)
        context['item_index'] = index
        context['item_count'] = count
        context['is_playing'] = self.auto
        context['is_paused'] = not self.auto
        context['COMMAND_CLOSE'] = COMMAND_CLOSE
        context['COMMAND_NEXT'] = COMMAND_NEXT
        context['COMMAND_PREVIOUS'] = COMMAND_PREVIOUS
        context['COMMAND_FIRST'] = COMMAND_FIRST
        context['COMMAND_LAST'] = COMMAND_LAST
        context['COMMAND_PLAY'] = COMMAND_PLAY
        context['COMMAND_PAUSE'] = COMMAND_PAUSE
        html = templates.render('default', item, context)
        return html
    def set_timer(self):
        if self.timer and self.timer.IsRunning():
            return
        self.timer = wx.CallLater(8000, self.on_timer)
    def stop_timer(self):
        if self.timer and self.timer.IsRunning():
            self.timer.Stop()
            self.timer = None
    def on_link(self, event):
        link = event.link
        if link == BLANK:
            event.Skip()
        elif link == COMMAND_CLOSE:
            self.on_close()
        elif link == COMMAND_FIRST:
            self.auto = False
            self.on_first()
        elif link == COMMAND_LAST:
            self.auto = False
            self.on_last()
        elif link == COMMAND_NEXT:
            self.auto = False
            self.on_next()
        elif link == COMMAND_PREVIOUS:
            self.auto = False
            self.on_previous()
        elif link == COMMAND_PLAY:
            if not self.auto:
                self.auto = True
                self.stop_timer()
                self.on_timer()
        elif link == COMMAND_PAUSE:
            self.auto = False
        else:
            webbrowser.open(link)
    def on_first(self):
        self.index = 0
        self.update()
    def on_last(self):
        self.index = self.count - 1
        self.update()
    def on_next(self):
        self.index += 1
        if self.index >= self.count:
            #self.index = self.count - 1
            self.on_close()
        else:
            self.update()
    def on_previous(self):
        self.index -= 1
        if self.index < 0:
            self.index = 0
        self.update()
    def on_close(self):
        self.stop_timer()
        self.clear_cache()
        event = Event(self, EVT_POPUP_CLOSE)
        wx.PostEvent(self, event)
    def on_timer(self):
        self.timer = None
        if not self.auto:
            return
        if self.index == self.count - 1:
            self.on_close()
        else:
            self.on_next()
            self.set_timer()
            