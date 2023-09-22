"""
ExpressMpeg
===========

A simple software to convert audio formats using ffmpeg.
This software is not made with some fancy GUIs unlike some other converters.
This software is free, open source.

email: exp

copyright: (c) 2023 ExpressMpeg.
license: MIT, see LICENSE for more details.

"""

import time
sartup_time = time.time()

from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.uic.load_ui import loadUi
import windows
from qframelesswindow import AcrylicWindow, FramelessDialog, WindowEffect

# ffmpeg tools
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError, CouldntEncodeError

# Treading, which will be wrapped by coroutine
from threading import Thread

# Other utils
import json
import sys
import os
import webbrowser


# Run app before configuration
app = QApplication(sys.argv)

# Import configuration file
from settings import *

# FileIcon provider
icon_provider = QFileIconProvider()

Information = 'Information'
Critical = 'Critical'
Question = 'Question'
Warning = 'Warning'
NoIcon = 'NoIcon'


__version__ = "1.1.1"

class ExpressMpegException:
    """ This is more a GUI alert than a real pythonic exception """
    def __init__(self, icon: str, title: str, text: str, buttons: QMessageBox.StandardButton = ...):
        log(f'ExpressMpegException -> Warning app with title: "{title}", text: "{text}"')
        if window.isMinimized():
            if QSystemTrayIcon.isSystemTrayAvailable():
                log(f'ExpressMpegException -> Warned with system trail')
                app_icon = QSystemTrayIcon(QIcon("./favicon.png"), parent=None)
                app_icon.activated.connect(lambda: print('hello'))
                app_icon.show()
                app_icon.showMessage(title, text, QSystemTrayIcon.MessageIcon.Information, 5000)
                return
            log(f'ExpressMpegException -> No system trail provided')
        
        log(f'ExpressMpegException -> Warned with QMessageBox')
        msg = QMessageBox(getattr(QMessageBox.Icon, icon), title, text, buttons, parent=window)
        self.code = msg.exec()

class NoExtentionFileError(ExpressMpegException):
    def __init__(self, text:str):
        log(f'NoExtentionFileError -> Error: "{text}"')
        super().__init__(icon=Warning, title="No extention found", text=text, buttons=QMessageBox.StandardButton.Ok)

class ConvertingFinished(ExpressMpegException):
    def __init__(self, text:str):
        log(f'NoExtentionFileError -> Info: "{text}"')
        super().__init__(icon=Information, title="Convertion finished!", text=text, buttons=QMessageBox.StandardButton.Ok)


class State:
    """ State of a song inside the coroutine """
    waiting = 'Waiting...'
    processing = 'Processing...'
    finished = 'Finished!'
    pause = 'Pause...'



class Song(QWidget):
    """ Class for songs. It inherits from QWidget to form a QListWidget """
    def __init__(self, app, list_item, file_name, output_folder=OUTPUT_FOLDER):
        """Infos on songs, output folder, ect..."""
        super().__init__(app)
        log(f'Song.__init__ -> building song for file "{file_name}"')
        self.app = app
        self.list_item = list_item


        self.file_name = file_name
        self.ext = Tools.extract_file_type(file_name)
        self.output_file = None
        self.to_format = None
        self.output_folder = output_folder
        self.delete_after = False
        if self.ext in file_types:
            file_types[self.ext].register(self)
        else:
            f = FileType(self.ext)
            file_types[self.ext] = f
            f.register(self)
        self.gui_manager()
        self.destroyed = False
        self.converting = False
        self.mk_dir = False

    def gui_manager(self):
        """ Loads the gui """
        loadUi('./windows/list-item.ui', self)
        self.label.setText(self.file_name)
        self.trashButton.clicked.connect(self.trash)
        self.playButton.clicked.connect(self.play)
        file_icon = icon_provider.icon(QFileInfo(self.file_name))
        # Set the icon to the QLabel
        self.iconLabel.setPixmap(file_icon.pixmap(20, 20))
        log(f'Song.gui_manager -> loaded gui for "{self.file_name}" with success')
    
    def play(self):
        os.system(f'"{self.file_name}"')
        log('Song.play -> Played song with success')
    
    def setText(self, text):
        """ Set the name of the list item """
        self.label_2.setText(text)
    
    def delete(self):
        """ Destroys item in list view"""
        row = self.app.listWidget.row(self.list_item)
        self.app.listWidget.takeItem(row)
        self.destroyed = True
        if self.delete_after:
            os.remove(self.file_name)
        log(f'Song.delete -> deleted "{self.file_name}" with success')

    def trash(self):
        file_types[self.ext].unregister(self)
    
    def setState(self, state:State = None):
        """ Sets the state label to a state """
        if state == State.finished:
            self.trash()
        if not self.destroyed:
            self.state_label.setText(state)
    
    def disable(self):
        self.trashButton.setEnabled(False)
        self.playButton.setEnabled(False)


    


class FileType:
    def __init__(self, ext):
        self.ext = ext
        self.in_use = False
        self._songs:list[Song] = []
    
    def register(self, song:Song):
        self._songs.append(song)
        self.in_use = True

    def unregister(self, song:Song):
        song.delete()
        del self._songs[self._songs.index(song)]
        if not self._songs:
            self.in_use = False
    
    def set_property(self, ext, output_folder, delete_after):
        for song in self._songs:
            file_name = song.file_name
            song.delete_after = delete_after
            _output_folder = OUTPUT_FOLDER + '/' + Tools.get_parent_folder(file_name) if output_folder else Tools.get_output_folder(file_name)
            song.output_file = Tools.get_output_path(file_name, ext, _output_folder)
            song.output_folder = _output_folder
            song.mk_dir = output_folder

    def get_songs_to_convert(self):
        return self._songs
    
    def reset(self):
        for x in self._songs:
            x.delete()
        self._songs = []
        self.in_use = False



class ActionItem(QWidget):
    def __init__(self, app, file_type:FileType):
        super().__init__(app)

        self.file_type = file_type
        self.load_ui('./windows/action-item.ui')

        self.outCombo.addItems(Tools._ext)
        self.ext_label.setText(file_type.ext)
    
    def load_ui(self, ui):
        loadUi(ui, self)
    
    def update(self):
        ext = self.outCombo.currentText()
        output = True if self.radioButtonOutput.isChecked() else False
        delete_after = self.checkBoxDelete.isChecked()
        self.file_type.set_property(ext, output, delete_after)
    


class Startup(QDialog):
    def __init__(self, app, file_types):
        super().__init__(app)
        self.app = app
        self.load_ui('./windows/start-dialog.ui')
        self.setWindowTitle('Start Config')

        for ext in file_types.keys():
            type = file_types[ext]
            if type.in_use:
                self.add_action(type)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
    
    def load_ui(self, ui):
        log("Sartup.load_ui -> loading ui")
        loadUi(ui, self)
        log("Sartup.load_ui -> builded ui with success")
    
    def add_action(self, type):
        widget = ActionItem(self, type)
        self.buttonBox.accepted.connect(widget.update)
        item = QListWidgetItem()
        item.setSizeHint(widget.sizeHint())
        self.listWidget.addItem(item)
        self.listWidget.setItemWidget(item, widget)



class Settings(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        log("Settings.init_ui -> loading ui")
        loadUi("windows/settings.ui", self)
        self.longSpinBox.setValue(int(WIN_SIZE.toSizeF().width()))
        self.heighSpinBox.setValue(int(WIN_SIZE.toSizeF().height()))
        self.openButton.setIcon(QIcon(icon_provider.icon(QFileIconProvider.IconType.Folder).pixmap(16, 16)))
        self.fileLineEdit.setText(OUTPUT_FOLDER)
        self.semaphoreSpinBox.setValue(SEMAPHORE)
        self.extComboBox.addItems(Tools._ext)
        log("Settings.init_ui -> builded ui with success")


class Convert:
    def __init__(self, song_file:Song):
        log("Converting.__init__ -> creating Thread pool")
        self.song_file = song_file
        def target():
            song_file.setState(State.processing)
            file = AudioSegment.from_file(song_file.file_name)
            if song_file.mk_dir:
                if not os.path.isdir(song_file.output_folder):
                    os.mkdir(song_file.output_folder)
            file.export(song_file.output_file)

        self.thread = Thread(target=target)
        log("Converting.__init__ -> successfuly created Thread pool")

    def __await__(self):
        self.thread.start()
        alive = True
        while alive:
            self.song_file.converting = True
            yield
            alive = self.thread.is_alive()
        self.song_file.setState(State.finished)



async def coro_wrapper(song_file:Song):
    log(f'coro_wrapper -> coroutine wrapper for file "{song_file.file_name}"')
    song_file.setState(State.waiting)
    convert = Convert(song_file)
    log("coro_wrapper -> starting awaiting")
    await convert
    log("coro_wrapper -> awaited with success")



class Loop:

    current = None
    
    def __init__(self):
        log("Loop.__init__ -> building loop")
        self.tasks = []
        self.queue = []
        self.pause = False
        
    def run(self, *songs):
        log("Loop.run: sarting loop")
        for task in songs:
            if hasattr(task, '__await__'):
                task: Convert = task.__await__()
            self.queue.append(task)
        Loop.current = self
        running = True
        while running:
            if len(self.tasks) < SEMAPHORE:
                if len(self.queue) >= SEMAPHORE:
                    for x in range(0, SEMAPHORE):
                        self.tasks.append(self.queue.pop(0))
                elif self.queue:
                    self.tasks.append(self.queue.pop(0))
            task = self.tasks.pop(0)
            try:
                next(task)
            except StopIteration:
                pass
            else:
                self.tasks.append(task)
            running = bool(self.tasks)
            QApplication.processEvents()
            if self.pause:
                log("Loop.run -> converting paused")
                for song in get_songs():
                    song.setState(State.pause)
                while self.pause:
                    QApplication.processEvents()
                for song in get_songs():
                    if song.converting:
                        song.setState(State.processing)
                    else:
                        song.setState(State.waiting)
                log("Loop.run -> converting resumed")
        log("Loop.run: exited loop process with success")




class Tools:
    _data = []
    _ext = []
    for _x in os.listdir('./supported'):
        with open(f'./supported/{_x}', 'rb') as _f:
            _raw = json.load(_f)
            _data.append(_raw)
            _ext.append('.'+_raw['ext'])

    @staticmethod
    def get_description():
        s = 'All supported files ('
        for x in Tools._data:
            s += f"*.{x['ext']}; "
        s = s[:-2] + ');;'
        for x in Tools._data:
            s += x['description'] + ";;"
        return s + "All Files (*)"

    @staticmethod
    def extract_file_types(files):
        types = set()
        for name in files:
            types.add('.' + name.split('.')[-1])
        return types
    
    @staticmethod
    def extract_file_type(file):
        return '.' + file.split('.')[-1]
    
    @staticmethod
    def class_by_file_type(files):
        types = dict()
        for name in files:
            type = Tools.extract_file_type(name)
            if type in types:
                types[type].append(name)
            else:
                types[type] = [name]
        return types
    
    @staticmethod
    def get_parent_folder(path:str):
        return path.split('/')[-2]
    

    @staticmethod
    def get_output_path(fpath:str, ext, tdir:str=OUTPUT_FOLDER):
        if '.' in fpath:    return tdir + '/' + fpath.split('/')[-1].split('.')[0] + ext
        else:               raise NoExtentionFileError(HELP_URL)
    
    @staticmethod
    def get_output_folder(path:str):
        return str().join([x + '/' for x in path.split('/')[0:-1]])

class About(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        loadUi('windows/about.ui', self)
        self.pushButton.clicked.connect(lambda: webbrowser.open_new_tab("https://github.com/ExpressMpeg/source"))

class Main(AcrylicWindow):
    def __init__(self) -> None:
        log("Main.__init__ -> initializing AcrylicWindow")
        super().__init__()
        print(os.path.abspath(OUTPUT_FOLDER))
        self.load_ui()
        self.resize(WIN_SIZE)
        self.setWindowIcon(FAV_ICON)
        self.addButton.clicked.connect(self.add_files)
        self.outButton.clicked.connect(lambda: os.system(f'explorer.exe "{os.path.abspath(OUTPUT_FOLDER)}"'))
        self.settingsButton.clicked.connect(self.settings)
        self.helpButton.clicked.connect(lambda: About(self).exec())
        self.startButton.clicked.connect(self.start)
        self.setWindowTitle('ExpressMpeg')
        self.running = False
        self.pause = False

    def dragEnterEvent(self, event):
        log("Main.dragEnterEvent")
        if event.mimeData().hasUrls() and not all(os.path.isdir(url.toLocalFile()) for url in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            file_paths = []
            for url in mime_data.urls():
                file = url.toLocalFile()
                if os.path.isfile(file):
                    file_paths.append(file)
            if file_paths:
                self.populate(file_paths)
                log("Main.dropEvent -> added_files with success")
            else:
                log("Main.add_files -> no files added")


    def load_ui(self):
        loadUi('./windows/main-window.ui', self)
        self.windowEffect.setMicaEffect(self.winId())
        log("Main.load_ui -> loaded ui with success")
        

    def add_files(self):
        log("Main.add_files -> starting File Dialog")
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Add Files", "", Tools.get_description())
        if file_paths:
            self.populate(file_paths)
            log("Main.add_files -> added_files with success")
        else:
            log("Main.add_files -> no files added")
    

    def populate(self, files:list):
        log(f"Main.populate -> populated {files}")
        file_names = [x.file_name for x in get_songs()]
        for name in files:
            if name in file_names:
                files.remove(name)
                if len(files) > 1:
                    continue
                elif len(files) == 1:
                    name = files[0]
                else:
                    break
            item = QListWidgetItem()
            widget = Song(self, item, name)
            item.setSizeHint(widget.sizeHint())
            self.listWidget.addItem(item)
            self.listWidget.setItemWidget(item, widget)
            QApplication.processEvents()
        log("Main.populate -> populated with success")


    def settings(self):
        log("Main.settings -> open settings dialog")
        dialog = Settings(self)
        dialog.exec()
    

    def start(self):
        if self.running:
            if hasattr(self, 'loop'):
                if self.loop.pause:
                    log("Main.start -> resuming")
                    self.startButton.setText("Pause")
                    self.loop.pause = False
                else:
                    log("Main.start -> pause")
                    self.loop.pause = True
                    self.startButton.setText("Resume")
        else:
            songs = get_songs()
            if songs:
                log("Main.start -> starting dialog")
                dialog = Startup(self, file_types)
                if dialog.exec():
                    log("Main.start -> closing starting dialog")
                    log("Main.start -> converting")
                    self.addButton.setEnabled(False)
                    [x.disable() for x in songs]
                    self.running = True
                    songs = [coro_wrapper(song) for song in songs]
                    self.startButton.setText("Pause")
                    self.loop = Loop()
                    self.loop.run(*songs)
                    delete_songs()
                    ConvertingFinished("Conversion of all files finished with success!")
                    log("Main.start -> converting finished with success")
                    self.startButton.setText("Start")
                    self.running = False
                    del self.loop
                    self.addButton.setEnabled(True)
                else:
                    log("sartup cancelled")
                

def get_songs() -> list[Song]:
    """ Gets all registered songs """
    songs = []
    for x in file_types.keys():
        songs.extend(file_types[x].get_songs_to_convert())
    return songs

def delete_songs():
    """ Deletes all songs """
    for x in file_types.keys():
        file_types[x].reset()
    window.files = []

_log = f"Sartup time: {time.time()-sartup_time}"+"\n"

def log(string):
    """ Adds a log for reporting bug """
    global _log
    _log +=  f"[{time.asctime()}] {string}" + '\n'

try:
    file_types: dict[str, FileType] = dict([x, FileType(x)] for x in Tools._ext)
    window = Main()
    window.show()
    code = app.exec()
except BaseException as e:
    print(e)
    code = 1
    log(e.__str__())

with open("./DEBUG.log", 'w') as f:
    log('__main__ -> Saving log...')
    log(f'__main__ -> Exit process with code {code}')
    f.write(_log+f"Total running time: {time.time()-sartup_time}")

sys.exit(code)
