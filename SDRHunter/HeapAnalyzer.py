#!/usr/bin/env python

import os
import sys
import math
import time

from PySide import QtCore, QtGui

import commons


class FreqDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        super(FreqDialog, self).__init__(parent)

        # Label
        title = QtGui.QLabel('Title')
        freq = QtGui.QLabel('Freq')
        bandwidth = QtGui.QLabel('Bandwidth')

        # Edit
        self.nameEdit = QtGui.QLineEdit()
        self.freqEdit = QtGui.QLineEdit()
        self.bandEdit = QtGui.QLineEdit()

        # Button
        okButton = QtGui.QPushButton("OK")
        okButton.setDefault(True)
        cancelButton = QtGui.QPushButton("Cancel")

        # Connect events
        okButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)

        # Prepare validation buttons
        hbox = QtGui.QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(okButton)
        hbox.addWidget(cancelButton)

        vbox = QtGui.QVBoxLayout()
        vbox.addStretch()
        vbox.addLayout(hbox)


        # Add edit section
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(title, 1, 0)
        grid.addWidget(self.nameEdit, 1, 1)

        grid.addWidget(freq, 2, 0)
        grid.addWidget(self.freqEdit, 2, 1)

        grid.addWidget(bandwidth, 3, 0)
        grid.addWidget(self.bandEdit, 3, 1)

        grid.addLayout(vbox, 4, 1)

        self.setLayout(grid)
        self.setGeometry(300, 300, 350, 50)
        self.setWindowTitle('Review')

    def createButton(self, text, member):
        button = QtGui.QPushButton(text)
        button.clicked.connect(member)
        return button

    def browse(self):
        directory = QtGui.QFileDialog.getExistingDirectory(self, "Find Files",
                                                           QtCore.QDir.currentPath())

        if directory:
            if self.directoryComboBox.findText(directory) == -1:
                self.directoryComboBox.addItem(directory)

            self.directoryComboBox.setCurrentIndex(self.directoryComboBox.findText(directory))

    def find(self):
        self.filesTable.setRowCount(0)

        fileName = self.fileComboBox.currentText()
        text = self.textComboBox.currentText()
        path = self.directoryComboBox.currentText()

        self.updateComboBox(self.fileComboBox)
        self.updateComboBox(self.textComboBox)
        self.updateComboBox(self.directoryComboBox)

        self.currentDir = QtCore.QDir(path)
        if not fileName:
            fileName = "*"
        files = self.currentDir.entryList([fileName],
                                          QtCore.QDir.Files | QtCore.QDir.NoSymLinks)

        if text:
            files = self.findFiles(files, text)
        self.showFiles(files)


class ExportDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        super(ExportDialog, self).__init__(parent)

        # Edit
        self.exportEdit = QtGui.QTextEdit()

        # Button
        # buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        # buttonBox.accepted(self.valid)

        # Add edit section
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(self.exportEdit)
        #grid.addWidget(buttonBox)

        self.setLayout(grid)
        self.setGeometry(100, 100, 640, 640)
        self.setWindowTitle('Review')


class FreqItem(QtGui.QTableWidgetItem):
    def __lt__(self, other):
        return (commons.hz2Float(self.data(QtCore.Qt.DisplayRole)) <
                commons.hz2Float(other.data(QtCore.Qt.DisplayRole)))


class MyTableModel(QtCore.QAbstractTableModel):
    def __init__(self, parent, mylist, header, *args):
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.mylist = mylist
        self.header = header

    def rowCount(self, parent):
        return len(self.mylist)

    def columnCount(self, parent):
        if self.rowCount(parent) == 0:
            return 0

        return len(self.mylist[0])

    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None

        return self.mylist[index.row()][index.column()]

    def headerData(self, col, orientation, role):
        if orientation == QtCore.Qt.Orientation.Horizontal and role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self.header[col]
        return None


class FreqScene(QtGui.QGraphicsScene):
    maxstep = 3
    stepmove, stepbandwidth, stepselected = range(maxstep)
    modeselect, modeleft, modecenter, moderight = range(4)
    linecurrentcolor, lineselectedcolor = (QtCore.Qt.red, QtCore.Qt.green)
    linebandwidthcolor, horizontalline = (QtCore.Qt.magenta, QtCore.Qt.gray)

    def __init__(self, parent=None):
        super(FreqScene, self).__init__(parent)

        self.heatmap = None
        self.ruler = None
        self.legend = None

        self.freqstart = 0
        self.freqend = 0
        self.freqstep = 0
        self.myMode = self.modecenter
        self.line = None

        self.mousestep = FreqScene.stepmove
        self.linefreq = None
        self.linetime = None
        self.rectbandwidth = None
        self.setBackgroundBrush(QtCore.Qt.black)

    def setMode(self, mode):
        self.myMode = mode

    def setFreqRange(self, freqstart, freqend, freqstep):
        self.freqstart = freqstart
        self.freqend = freqend
        self.freqstep = freqstep

    def Hz2Pos(self, freq):
        return (freq - self.freqstart) / self.freqstep

    def Pos2Hz(self, posx):
        return self.freqstart + (posx * self.freqstep)

    def generateHeatmap(self, datas):
        # Try load file
        image = QtGui.QImage(datas.summaries['samples']['nbsamplescolumn'], datas.summaries['samples']['nblines'],
                             QtGui.QImage.Format_RGB32)

        y = 0
        for line in datas.samples:
            x = 0
            for sample in line:
                g = datas.power2RGB(sample)
                rgb = QtGui.qRgb(int(g * 255), int(g * 255), 50)

                image.setPixel(x, y, rgb)
                x += 1

            y += 1

        return QtGui.QPixmap.fromImage(image)

    def wheelEvent(self, e):

        if e.modifiers() & QtCore.Qt.ControlModifier:
            if e.delta() < 0:
                self.views()[0].scale(0.95, 0.95)
            else:
                self.views()[0].scale(1.05, 1.05)
            e.accept()


    def mouseReleaseEvent(self, mouseEvent):
        if self.line and self.myMode == self.InsertLine:
            startItems = self.items(self.line.line().p1())
            if len(startItems) and startItems[0] == self.line:
                startItems.pop(0)
            endItems = self.items(self.line.line().p2())
            if len(endItems) and endItems[0] == self.line:
                endItems.pop(0)

            self.removeItem(self.line)
            self.line = None

        self.line = None
        super(FreqScene, self).mouseReleaseEvent(mouseEvent)


class RulerItem(QtGui.QGraphicsItem):
    def __init__(self):
        self.bigheight = 15
        self.middleheight = 10
        self.smallheight = 4
        self.supersmallheight = 2

        # Load Font
        dirname = os.path.dirname(os.path.realpath(__file__))
        fontfilename = os.path.join(dirname, "Vera.ttf")
        fontid = QtGui.QFontDatabase.addApplicationFont(fontfilename);
        self.font = QtGui.QFont(QtGui.QFontDatabase.applicationFontFamilies(fontid)[0], 10)

        QtGui.QGraphicsItem.__init__(self)

    def boundingRect(self):
        return QtCore.QRectF(QtCore.QPointF(0, 0), QtCore.QSizeF(self.scene().width(), self.height()))

    def height(self):
        fm = QtGui.QFontMetrics(self.font)
        return self.bigheight + fm.height()

    def paint(self, painter, options, widget):
        painter.setPen(
            QtGui.QPen(QtCore.Qt.white, 1, QtCore.Qt.SolidLine))  # , QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))

        gradientinterval = [1000, 5000, 10000, 50000, 100000, 500000, 1000000, 5000000, 10000000, 50000000, 100000000]
        grandientheights = [self.supersmallheight, self.smallheight, self.middleheight, self.bigheight]

        fm = QtGui.QFontMetrics(self.font)
        posheight = -1
        for ginterval in gradientinterval:
            if posheight < len(grandientheights) - 1:
                mess = commons.float2Hz(self.scene().freqend)
                widthinterval = ginterval / self.scene().freqstep
                if widthinterval >= 3:
                    posheight += 1
                    for freq in range(0, int(self.scene().freqend - self.scene().freqstart), ginterval):
                        posx = freq / self.scene().freqstep
                        line = QtCore.QLineF(QtCore.QPointF(posx, self.height() - grandientheights[posheight]),
                                             QtCore.QPointF(posx, self.height()))

                        painter.drawLine(line)
                        painter.setFont(self.font)

                textwidth = fm.width(mess)
                if textwidth * 1 < widthinterval:
                    for freq in range(0, int(self.scene().freqend - self.scene().freqstart), ginterval):
                        posx = freq / self.scene().freqstep
                        textpos = posx - (textwidth / 2)
                        if textpos > 0:
                            mess = commons.float2Hz(freq + self.scene().freqstart)
                            painter.drawText(QtCore.QRectF(textpos, 0, textwidth + (textwidth / 2), fm.height()), mess)
                            painter.setFont(self.font)


class LegendItem(QtGui.QGraphicsItem):
    def __init__(self, parent):
        self.parent = parent
        self.bigheight = 15
        self.middleheight = 8
        self.smallheight = 3

        # Load Font
        dirname = os.path.dirname(os.path.realpath(__file__))
        fontfilename = os.path.join(dirname, "Vera.ttf")
        fontid = QtGui.QFontDatabase.addApplicationFont(fontfilename);
        self.fontsize = 10
        self.font = QtGui.QFont(QtGui.QFontDatabase.applicationFontFamilies(fontid)[0], self.fontsize)
        fm = QtGui.QFontMetrics(self.font)
        self.textsizey = fm.height()

        # For legend drawing
        self.legends_row = []
        self.spacebefore = 2
        self.lineordotpos = 7
        self.centerline = 5
        self.spaceafter = 4
        self.totallineheight = self.spacebefore + self.lineordotpos + self.centerline + self.textsizey + self.spaceafter
        self.legends_height = 0

        QtGui.QGraphicsItem.__init__(self)

    def boundingRect(self):
        return QtCore.QRectF(QtCore.QPointF(0, 0), QtCore.QSizeF(self.scene().width(), self.height()))

    def height(self):
        return self.legends_height

    def paint(self, painter, options, widget):

        nb_lines = len(self.legends_row)
        last_line_xpos = [0] * nb_lines
        for nbline in range(nb_lines):
            for legend in self.legends_row[nbline]:
                ypos = nbline * self.totallineheight
                textsizex = legend['textright'] - legend['textleft']
                if legend['textleft'] >= 0 or 1 == 1:
                    painter.setPen(
                        QtGui.QPen(QtCore.Qt.white, 1, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
                    painter.drawText(legend['textleft'], ypos + self.lineordotpos + self.centerline, textsizex,
                                     self.textsizey, QtCore.Qt.AlignHCenter, legend['name'])
                    last_line_xpos[nbline] = legend['textleft'] + textsizex

                    # Check if bandwith in the same point
                    if int(legend['posright'] - legend['posleft']) > 5:
                        line = QtCore.QLineF(legend['posleft'] + 1, ypos + self.lineordotpos, legend['posright'] - 1,
                                             ypos + self.lineordotpos)
                        painter.drawLine(line)
                        line = QtCore.QLineF(legend['poscenter'], ypos + self.lineordotpos, legend['poscenter'],
                                             ypos + self.lineordotpos + self.centerline)
                        painter.drawLine(line)


                        # Draw left limit
                        if legend['posleft'] < 0:
                            painter.setPen(QtGui.QPen(QtCore.Qt.black, 1, QtCore.Qt.DotLine, QtCore.Qt.RoundCap,
                                                      QtCore.Qt.RoundJoin))
                            line = QtCore.QLineF(0, ypos + self.lineordotpos, 20, ypos + self.lineordotpos)
                            painter.drawLine(line)
                        else:
                            painter.setPen(QtGui.QPen(QtCore.Qt.white, 1, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap,
                                                      QtCore.Qt.RoundJoin))
                            line = QtCore.QLineF(legend['posleft'] + 1, ypos + self.lineordotpos, legend['posleft'] + 1,
                                                 ypos + self.lineordotpos - 7)
                            painter.drawLine(line)

                        # Draw right limit
                        if legend['posright'] > self.scene().width():
                            painter.setPen(QtGui.QPen(QtCore.Qt.black, 1, QtCore.Qt.DotLine, QtCore.Qt.RoundCap,
                                                      QtCore.Qt.RoundJoin))
                            line = QtCore.QLineF(self.scene().width() - 20, ypos + self.lineordotpos,
                                                 self.scene().width(), ypos + self.lineordotpos)
                            painter.drawLine(line)
                        else:
                            painter.setPen(QtGui.QPen(QtCore.Qt.white, 1, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap,
                                                      QtCore.Qt.RoundJoin))
                            line = QtCore.QLineF(legend['posright'] - 1, ypos + self.lineordotpos,
                                                 legend['posright'] - 1, ypos + self.lineordotpos - 7)
                            painter.drawLine(line)
                    else:
                        rect = QtCore.QRectF(legend['poscenter'] - 1, ypos + (self.lineordotpos / 2), 2, 2)
                        painter.fillRect(rect, QtGui.QBrush(QtCore.Qt.cyan))


    def updateLegendSize(self, jsonstations):
        # Search legends can be show in heatmap
        legends_can_draw = []

        for jsoncontent in jsonstations:
            for station in jsoncontent['stations']:
                if 'name' in station:
                    if 'freq_left' in station:
                        station['freq_left'] = commons.hz2Float(station['freq_left'])
                        station['freq_right'] = commons.hz2Float(station['freq_right'])
                        station['bw'] = station['freq_right'] - station['freq_left']
                        station['freq_center'] = station['freq_left'] + (station['bw'] / 2)
                    else:
                        station['freq_center'] = commons.hz2Float(station['freq_center'])
                        station['bw'] = commons.hz2Float(station['bw'])
                        station['freq_left'] = station['freq_center'] - (station['bw'] / 2)
                        station['freq_right'] = station['freq_left'] + station['bw']

                    # Calc Cropped freq (for drawing in heatmap)
                    fm = QtGui.QFontMetrics(self.font)
                    textsizex = fm.width(station['name'])
                    station['cropped_left'] = max(station['freq_left'], self.scene().freqstart - self.scene().freqstep)
                    station['cropped_right'] = min(station['freq_right'], self.scene().freqend + self.scene().freqstep)
                    station['cropped_bw'] = station['cropped_right'] - station['cropped_left']
                    station['cropped_center'] = station['cropped_left'] + (station['cropped_bw'] / 2)
                    station['posleft'] = (station['cropped_left'] - self.scene().freqstart) / self.scene().freqstep
                    station['poscenter'] = (station['cropped_center'] - self.scene().freqstart) / self.scene().freqstep
                    station['posright'] = (station['cropped_right'] - self.scene().freqstart) / self.scene().freqstep
                    station['textleft'] = ((station[
                                                'cropped_center'] - self.scene().freqstart) / self.scene().freqstep) - (
                                              textsizex / 2)
                    station['textright'] = ((station[
                                                 'cropped_center'] - self.scene().freqstart) / self.scene().freqstep) + (
                                               textsizex / 2)
                    # calc min and max position (line or text)
                    station['cropminleft'] = min(station['posleft'], station['textleft'])
                    station['cropmaxright'] = max(station['posright'], station['textright'])

                    if 0 <= station['cropminleft'] <= self.scene().width() or \
                                            0 <= station['cropmaxright'] <= self.scene().width():
                        legends_can_draw.append(station)
                    else:
                        if station['cropminleft'] <= 0 and station['cropmaxright'] >= self.scene().width():
                            legends_can_draw.append(station)


        # Order legends by bandwith
        legends_can_draw = sorted(legends_can_draw, key=lambda x: x['bw'], reverse=True)

        self.legends_row = []
        for station in legends_can_draw:
            append_in_same_line = False
            for lineidx in range(len(self.legends_row)):
                nbcolumns = len(self.legends_row[lineidx])
                # Check if can i append the freq
                if nbcolumns > 0:
                    if station['cropminleft'] >= self.legends_row[lineidx][nbcolumns - 1]['cropmaxright'] or \
                                    station['cropmaxright'] <= self.legends_row[lineidx][0]['cropminleft']:
                        append_in_same_line = True
                        break

                if nbcolumns > 1:
                    for column in range(1, nbcolumns):
                        if station['cropminleft'] >= self.legends_row[lineidx][column - 1]['cropmaxright'] and \
                                        station['cropmaxright'] <= self.legends_row[lineidx][column]['cropminleft']:
                            append_in_same_line = True
                            break

                if append_in_same_line == True:
                    break

            if append_in_same_line:
                self.legends_row[lineidx].append(station)
                self.legends_row[lineidx] = sorted(self.legends_row[lineidx], key=lambda x: x['cropminleft'])
            else:
                maxnb_lines = self.parent.sdrdatas.scaninfo['global']['heatmap']['maxnb_lines']
                if len(self.legends_row) + 1 <= maxnb_lines:
                    self.legends_row.append([])
                    self.legends_row[len(self.legends_row) - 1].append(station)

        self.legends_row.reverse()
        self.legends_height = len(self.legends_row) * self.totallineheight


class MainWindow(QtGui.QMainWindow):
    InsertTextButton = 10
    InsertImgButton = 99

    image = None
    summary = None

    def __init__(self):
        super(MainWindow, self).__init__()

        self.current_pos = None
        self.selected_center_pos = None
        self.bandwidth_pixels = -1

        self.current_centerfreq = 0
        self.bwfreq = 0
        self.filefreqs = ''
        self.sdrdatas = None
        self.jsonstations = []
        self.rootdir = {}

        self.createActions()
        self.createMenus()
        self.createToolbars()
        self.initScene()

        # Ajout des composants dans le layout
        hlayout = QtGui.QHBoxLayout()
        # hlayout.addWidget(self.toolBox)

        # Create Freq Dialog
        self.freqdialog = FreqDialog()
        self.exportdialog = ExportDialog()

        # Create Table view
        self.createTbView()

        # Create view
        self.view = QtGui.QGraphicsView(self.scene)
        self.view.setMouseTracking(True)
        # self.view.setFocusPolicy(QtCore.Qt.NoFocus)

        hlayout.addWidget(self.view)

        self.widget = QtGui.QWidget()
        self.widget.setLayout(hlayout)

        self.setCentralWidget(self.widget)
        self.setWindowTitle("Diagramscene")


    def save2Image(self):
        (filename, ext) = os.path.splitext(self.sdrdatas.csvfilename)
        imgfile = '%s%s' % (filename, '.png')
        exists = os.path.exists(imgfile)
        if not exists:
            image = QtGui.QImage(self.scene.sceneRect().size().width(), self.scene.sceneRect().size().height(),
                                 QtGui.QImage.Format_ARGB32)
            painter = QtGui.QPainter(image)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            self.scene.render(painter)
            image.save(imgfile)


    def selectHeatmapFile(self):
        fullname, _ = QtGui.QFileDialog.getOpenFileName(self, "Open File", self.rootdir)
        if fullname != '':
            self.loadDatas(fullname)
            self.updateScene()


    def export2TXT(self):
        jsonfreqs = self.tablefreq2JSON()

        lines = []
        for station in jsonfreqs['stations']:
            lines.append("%s %s" % (station['freq_center'], station['name']))

        text = '\n'.join(lines)
        self.exportdialog.exportEdit.setText(text)
        self.exportdialog.exec_()  # == QtGui.QDialog.Accepted:


    def initScene(self):
        self.scene = FreqScene(self)
        self.scene.setSceneRect(QtCore.QRectF(0, 0, 5000, 5000))
        self.scene.mouseMoveEvent = self.scn_mouseMoveEvent
        self.scene.mousePressEvent = self.scn_mousePressEvent

        # Add ruler
        self.scene.ruler = RulerItem()

        # Add Img
        self.scene.heatmap = QtGui.QGraphicsPixmapItem()

        # Add Freq Legend
        self.scene.legend = LegendItem(self)

        # Set freq line
        self.scene.linefreq = QtGui.QGraphicsLineItem()
        self.scene.linefreq.setPen(QtGui.QPen(self.scene.linecurrentcolor, 1))
        self.scene.linefreq.setOpacity(0.5)

        # Set time line
        self.scene.linetime = QtGui.QGraphicsLineItem()
        self.scene.linetime.setPen(QtGui.QPen(self.scene.horizontalline, 1))
        self.scene.linetime.setOpacity(0.2)


        # Set rect bandwidth
        self.scene.rectbandwidth = QtGui.QGraphicsRectItem()
        self.scene.rectbandwidth.setPen(QtGui.QPen(QtCore.Qt.magenta, 1))
        self.scene.rectbandwidth.setBrush(QtGui.QBrush(QtCore.Qt.gray))
        self.scene.rectbandwidth.setOpacity(0.5)

        # Add items in the scene
        self.scene.addItem(self.scene.ruler)
        self.scene.addItem(self.scene.heatmap)
        self.scene.addItem(self.scene.legend)
        self.scene.addItem(self.scene.linefreq)
        self.scene.addItem(self.scene.linetime)
        self.scene.addItem(self.scene.rectbandwidth)


    def zoomIn(self):
        self.view.scale(1.25, 1.25)

    def zoomOut(self):
        self.view.scale(0.75, 0.75)

    def normalSize(self):
        self.imageLabel.adjustSize()
        self.scaleFactor = 1.0

    def fitToWindow(self):
        self.view.fitInView()


    def sceneScaleChanged(self, scale):
        newScale = int(scale[:-1]) / 100.0
        oldMatrix = self.view.matrix()
        self.view.resetMatrix()
        self.view.translate(oldMatrix.dx(), oldMatrix.dy())
        self.view.scale(newScale, newScale)

    def itemSelected(self, item):
        font = item.font()
        color = item.defaultTextColor()
        self.fontCombo.setCurrentFont(font)
        self.fontSizeCombo.setEditText(str(font.pointSize()))
        self.boldAction.setChecked(font.weight() == QtGui.QFont.Bold)
        self.italicAction.setChecked(font.italic())
        self.underlineAction.setChecked(font.underline())

    def clickeditemfreq(self, item):
        freqitem = self.tablefreq.item(item.row(), 0)
        bwitem = self.tablefreq.item(item.row(), 1)
        freqhz = commons.hz2Float(freqitem.text())
        bwhz = commons.hz2Float(bwitem.text())

        self.selected_center_pos = (self.scene.Hz2Pos(freqhz),0)
        self.bandwidth_pixels = bwhz / self.scene.freqstep
        # self.bandwidth_pixels = self.scene.Hz2Pos(freqhz + (bwhz / 2)) - self.selectedfreq

        vvalue = self.scene.views()[0].verticalScrollBar().value()
        currentviewport = self.scene.views()[0].viewport()
        self.scene.views()[0].centerOn(self.current_pos.x(), 0)
        self.scene.views()[0].verticalScrollBar().setValue(vvalue)

        self.scene.mousestep = FreqScene.stepselected
        self.updateFreqsData()

    def doubleclickeditemfreq(self, item):
        freqitem = self.tablefreq.item(item.row(), 0)
        bwitem = self.tablefreq.item(item.row(), 1)
        nameitem = self.tablefreq.item(item.row(), 2)

        values = {
            'freq_center': freqitem.text(),
            'bw': bwitem.text(),
            'name': nameitem.text()
        }
        self.showDialogFreq(item.row(), values)

    def showDialogFreq(self, rowid, values):
        # Fill the edit fields
        self.freqdialog.freqEdit.setText(values['freq_center'])
        self.freqdialog.bandEdit.setText(values['bw'])
        self.freqdialog.nameEdit.setText(values['name'])

        # Update de the result
        if self.freqdialog.exec_() == QtGui.QDialog.Accepted:
            edtresult = {
                'freq_center': self.freqdialog.freqEdit.text(),
                'bw': self.freqdialog.bandEdit.text(),
                'name': self.freqdialog.nameEdit.text()
            }
            self.insertOrUpdateFreq(rowid, edtresult)
            self.jsonstations[0] = self.saveFreqs()
            self.scene.legend.updateLegendSize(self.jsonstations)
            self.view.update()


    def insertOrUpdateFreq(self, rowid, values):
        if rowid == -1:
            rowid = self.tablefreq.rowCount()
            self.tablefreq.insertRow(rowid)

        # Items
        freqitem = FreqItem(values['freq_center'])
        bwitem = QtGui.QTableWidgetItem(values['bw'])
        nameitem = QtGui.QTableWidgetItem("")
        if 'name' in values:
            nameitem.setText(values['name'])

        self.tablefreq.setItem(rowid, 0, freqitem)
        self.tablefreq.setItem(rowid, 1, bwitem)
        self.tablefreq.setItem(rowid, 2, nameitem)

    def deleteFreqs(self, rows):

        # Get all row index
        indexes = []
        for row in rows:
            indexes.append(row.row())

        # Reverse sort
        indexes = sorted(indexes, reverse=True)

        # Delete rows
        for rowidx in indexes:
            self.tablefreq.removeRow(rowidx)

        # Save freqs to file
        self.jsonstations[0] = self.saveFreqs()
        self.scene.legend.updateLegendSize(self.jsonstations)
        self.view.update()

    def tablefreq2JSON(self, ignoreNotIdentified=False):
        rowcount = self.tablefreq.rowCount()
        self.tablefreq.sortItems(0)

        jsonfreqs = {'stations': []}
        for row in range(rowcount):
            freqitem = self.tablefreq.item(row, 0)
            bwitem = self.tablefreq.item(row, 1)
            nameitem = self.tablefreq.item(row, 2)

            item = {'freq_center': freqitem.text(), 'bw': bwitem.text(), 'name': nameitem.text()}
            jsonfreqs['stations'].append(item)

        return jsonfreqs

    def saveFreqs(self):
        jsonfreqs = self.tablefreq2JSON()
        exists = os.path.exists(self.filefreqs)
        if exists:
            os.rename(self.filefreqs, "%s.%s.backup" % (self.filefreqs, int(time.time())))
        commons.saveJSON(self.filefreqs, jsonfreqs)

        return jsonfreqs


    def loadStations(self, filename):
        jsondata = commons.loadJSON(filename)
        if not jsondata:
            jsondata = {'stations': []}

        return jsondata


    def createTbView(self):
        dock = QtGui.QDockWidget("Stations", self)
        dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)

        # Init table
        headers = ["Freq", "Bw", 'Name']
        self.tablefreq = QtGui.QTableWidget()
        self.tablefreq.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.tablefreq.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tablefreq.itemClicked.connect(self.clickeditemfreq)
        self.tablefreq.itemDoubleClicked.connect(self.doubleclickeditemfreq)

        self.tablefreq.setColumnCount(len(headers))
        self.tablefreq.setHorizontalHeaderLabels(headers)
        self.tablefreq.verticalHeader().hide()

        dock.setWidget(self.tablefreq)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)


    def createActions(self):
        # File
        self.openAction = QtGui.QAction("&Open", self, shortcut="Ctrl+O",
                                        statusTip="Open file", triggered=self.selectHeatmapFile)

        self.saveimageAction = QtGui.QAction("&Save image", self, shortcut="Ctrl+S",
                                             statusTip="Save to image", triggered=self.save2Image, enabled=False)

        self.exitAction = QtGui.QAction("E&xit", self, shortcut="Ctrl+X",
                                        statusTip="Quit Scenediagram example", triggered=self.close)

        # Export
        self.export2TXTAction = QtGui.QAction("Export to &Text", self, shortcut="Ctrl+B",
                                              statusTip="Export to Text format", triggered=self.export2TXT)

        # View
        self.zoomInAct = QtGui.QAction("ZoomIn", self, shortcut="Ctrl++",
                                       statusTip="Zoom In", triggered=self.zoomIn)

        self.zoomOutAct = QtGui.QAction("ZommOut", self, shortcut="Ctrl+-",
                                        statusTip="Zoom Out", triggered=self.zoomOut)

        self.normalSizeAct = QtGui.QAction("Normal", self, shortcut="Ctrl+0",
                                           statusTip="Normal", triggered=self.normalSize)

        self.fitToWindowAct = QtGui.QAction("Fit", self, shortcut="Ctrl+F",
                                            statusTip="Fit windows", triggered=self.fitToWindow)


    def createMenus(self):
        self.fileMenu = self.menuBar().addMenu("&File")
        self.fileMenu.addAction(self.openAction)
        self.fileMenu.addAction(self.saveimageAction)
        self.fileMenu.addAction(self.exitAction)

        self.exportMenu = self.menuBar().addMenu("&Export")
        self.exportMenu.setEnabled(False)
        self.exportMenu.addAction(self.export2TXTAction)

        self.viewMenu = self.menuBar().addMenu("&View")
        self.viewMenu.addAction(self.zoomInAct)
        self.viewMenu.addAction(self.zoomOutAct)
        self.viewMenu.addAction(self.normalSizeAct)
        self.viewMenu.addSeparator()
        self.viewMenu.addAction(self.fitToWindowAct)


    def createToolbars(self):
        # pointerButton = QtGui.QToolButton()
        # pointerButton.setCheckable(True)
        # pointerButton.setText("Pointer")
        #
        # selectleftfreqButton = QtGui.QToolButton()
        # selectleftfreqButton.setCheckable(True)
        # selectleftfreqButton.setText("USB")
        #
        # selectcenterfreqButton = QtGui.QToolButton()
        # selectcenterfreqButton.setCheckable(True)
        # selectcenterfreqButton.setChecked(True)
        # selectcenterfreqButton.setText("Center")
        #
        # selectrightfreqButton = QtGui.QToolButton()
        # selectrightfreqButton.setCheckable(True)
        # selectrightfreqButton.setText("LSB")

        self.sceneScaleCombo = QtGui.QComboBox()
        self.sceneScaleCombo.addItems(["50%", "75%", "100%", "125%", "150%", "200%", "300%", "400%", "600%", "1000%"])
        self.sceneScaleCombo.setCurrentIndex(2)
        self.sceneScaleCombo.currentIndexChanged[str].connect(self.sceneScaleChanged)

        self.stepfreq = QtGui.QSpinBox()
        self.stepfreq.setRange(0, 1000)
        self.stepfreq.setSingleStep(10)
        self.stepfreq.setSuffix(' Khz')
        self.stepfreq.setSpecialValueText("Automatic")
        self.stepfreq.setValue(100)

        # Labels
        self.lblcurrentfreq = QtGui.QLabel()
        self.lblselectedfreq = QtGui.QLabel()
        self.lblselectedbw = QtGui.QLabel()

        font = QtGui.QFont("Courier New", 16)
        font.setBold(True)

        # Load Font
        dirname = os.path.dirname(os.path.realpath(__file__))
        fontfilename = os.path.join(dirname, "LCDM2N__.TTF")
        fontid = QtGui.QFontDatabase.addApplicationFont(fontfilename)
        font = QtGui.QFont(QtGui.QFontDatabase.applicationFontFamilies(fontid)[0], 16)
        font.setBold(True)

        self.lblcurrentfreq.setToolTip("Current Freq")
        self.lblselectedfreq.setToolTip("Selected Freq")
        self.lblselectedbw.setToolTip("Bandwidth")

        self.lblcurrentfreq.setFont(font)
        self.lblselectedfreq.setFont(font)
        self.lblselectedbw.setFont(font)

        self.lblcurrentfreq.setStyleSheet('QLabel { color: red }')
        self.lblselectedfreq.setStyleSheet('QLabel { color: green }')
        self.lblselectedbw.setStyleSheet('QLabel { color: magenta }')

        self.lblcurrentfreq.setAlignment(QtCore.Qt.AlignCenter)
        self.lblselectedfreq.setAlignment(QtCore.Qt.AlignCenter)
        self.lblselectedbw.setAlignment(QtCore.Qt.AlignCenter)

        self.pointerToolbar = self.addToolBar("Select freq")
        # self.pointerToolbar.addWidget(pointerButton)
        # self.pointerToolbar.addWidget(selectleftfreqButton)
        # self.pointerToolbar.addWidget(selectcenterfreqButton)
        # self.pointerToolbar.addWidget(selectrightfreqButton)
        # self.pointerToolbar.addWidget(self.sceneScaleCombo)
        # self.pointerToolbar.addWidget(self.stepfreq)
        self.pointerToolbar.addWidget(self.lblcurrentfreq)
        self.pointerToolbar.addWidget(self.lblselectedfreq)
        self.pointerToolbar.addWidget(self.lblselectedbw)

    def keyPressEvent(self, e):
        ReduceBW = 81
        AugmentBW = 83

        pressedkey = e.key()

        # if pressedkey == ZoomIn:
        # #self.scene.bandwidthvalue += 1
        # self.zoomIn()
        #
        # if pressedkey == ZoomOut:
        #     self.zoomOut()
        #     #self.scene.bandwidthvalue -= 1

        # if pressedkey == AugmentBW:
        #     self.bandwidth_pos += 1
        #
        # if pressedkey == ReduceBW:
        #     self.bandwidth_pos -= 1

        if pressedkey == QtCore.Qt.Key_Delete:
            selectedrows = self.tablefreq.selectionModel().selectedRows()
            if len(selectedrows):
                self.deleteFreqs(selectedrows)

        if pressedkey == QtCore.Qt.Key_Space or pressedkey == QtCore.Qt.Key_Return:
            values = {
                'freq_center': commons.float2Hz(self.selectedfreq, 3),
                'bw': commons.float2Hz(self.bwfreq, 3),
                'name': 'NOT IDENTIFIED'
            }
            self.showDialogFreq(-1, values)

        self.updateFreqsData()

    def updateFreqsData(self):
        # Move bandwidth box
        if self.scene.myMode == self.scene.modecenter:
            left = -1
            if self.selected_center_pos:
                left = self.selected_center_pos.x() - self.bandwidth_pixels
            right = self.bandwidth_pixels * 2
        elif self.scene.myMode == self.scene.modeleft:
            left = -1
            if self.selected_center_pos:
                left = self.selected_center_pos.x() - self.bandwidth_pixels
            right = self.bandwidth_pixels
        elif self.myMode == self.moderight:
            left = -1
            if self.selected_center_pos:
                left = self.selected_center_pos.x()
            right = self.bandwidth_pixels

        if self.scene.mousestep == FreqScene.stepmove:
            # Freq line
            self.scene.linefreq.setPen(QtGui.QPen(self.scene.linecurrentcolor, 1))
            self.scene.linefreq.setLine(self.current_pos.x(), 0, self.current_pos.x(), self.scene.height())

            # Time line
            self.scene.linetime.setLine(0, self.current_pos.y(), self.scene.width(), self.current_pos.y())
            self.scene.linetime.setVisible(True)

            # Bandwidth
            self.scene.rectbandwidth.setVisible(False)

        else:
            # Freq line
            self.scene.linefreq.setPen(QtGui.QPen(self.scene.lineselectedcolor, 1))
            self.scene.linefreq.setLine(self.selected_center_pos.x(), 0, self.selected_center_pos.x(), self.scene.height())

            # Time line
            self.scene.linetime.setVisible(False)

            # Bandwidth
            self.scene.rectbandwidth.setRect(left, 0, right, self.scene.height())
            self.scene.rectbandwidth.setVisible(True)

        # Refresh label
        if self.current_pos != None:
            self.currentfreq = self.scene.Pos2Hz(self.current_pos.x())
            self.lblcurrentfreq.setText("Current: %sHz" % commons.float2Hz(self.currentfreq, 3))
        else:
            self.currentfreq = -1
            self.lblcurrentfreq.setText("")

        if self.selected_center_pos != None:
            self.selectedfreq = self.scene.Pos2Hz(self.selected_center_pos.x())
            self.lblselectedfreq.setText(" Selected: %sHz" % commons.float2Hz(self.selectedfreq, 3))
        else:
            self.selectedfreq = -1
            self.lblselectedfreq.setText("")

        if self.bandwidth_pixels != -1:
            self.bwfreq = (self.scene.Pos2Hz(self.bandwidth_pixels) - self.scene.freqstart) * 2
            self.lblselectedbw.setText(" Bandwidth: %sHz" % commons.float2Hz(self.bwfreq, 3))
        else:
            self.bwfreq = -1
            self.lblselectedbw.setText("")


    def scn_lostFocusEvent(self, event):
        self.lblcurrentfreq = ""

    def scn_mousePressEvent(self, mouseEvent):
        if (mouseEvent.button() != QtCore.Qt.LeftButton):
            return

        # Selected center freq
        if self.scene.mousestep == FreqScene.stepmove:
            self.selected_center_pos = self.current_pos

        self.scene.mousestep = (self.scene.mousestep + 1) % FreqScene.maxstep

        # Selected
        if self.scene.mousestep == FreqScene.stepmove:
            self.selected_center_pos = None
            self.bandwidth_pixels = -1
            self.selected_centerfreq = 0
            self.bwfreq = 0
            self.updateFreqsData()

        super(FreqScene, self.scene).mousePressEvent(mouseEvent)
        self.updateFreqsData()


    def scn_mouseMoveEvent(self, mouseEvent):
        # Begin freq selection
        self.current_pos = mouseEvent.scenePos()

        # Move cursor
        if self.scene.mousestep == FreqScene.stepmove:
            pass
            # self.selected_center_pos = self.current_pos
            # self.bandwidth_pos = 0

        # Begin bandwidth selection
        if self.scene.mousestep == FreqScene.stepbandwidth:
            self.bandwidth_pixels = math.fabs(self.selected_center_pos.x() - self.current_pos.x())
            self.bwfreq = math.fabs(self.current_pos.x() - self.currentfreq)
            if self.scene.myMode == self.scene.modecenter:
                self.bwfreq *= 2

        self.updateFreqsData()

    def loadDatas(self, filename):
        self.exportMenu.setEnabled(False)
        self.saveimageAction.setEnabled(False)

        exists = os.path.isfile(filename)
        if exists:
            iscsvfile = filename.rfind(".csv") > -1 or filename.rfind(".running") > -1
            if iscsvfile:
                # Load files
                self.sdrdatas = commons.SDRDatas(filename)

                # Load scan result
                self.jsonstations = []
                self.filefreqs = os.path.join(os.path.abspath(os.path.join(os.path.dirname(filename), '..')),
                                              "scanresult.json")
                self.jsonstations.append(self.loadStations(self.filefreqs))

                globalcfg = self.sdrdatas.scaninfo['global']
                for legend in self.sdrdatas.scaninfo['global']['heatmap']['stationsfilenames']:
                    self.jsonstations.append(self.loadStations(legend))

                # Add to table
                while self.tablefreq.rowCount() > 0:
                    self.tablefreq.removeRow(0)
                for data in self.jsonstations[0]['stations']:
                    self.insertOrUpdateFreq(-1, data)
                self.tablefreq.sortItems(0)
                self.tablefreq.resizeColumnsToContents()

                # Refresh status
                argumentcfg = self.sdrdatas.scaninfo['arguments']
                self.statusBar().showMessage("?[%s] @[%s] => %s" % (
                    argumentcfg['location']['name'],
                    globalcfg['author']['name'],
                    filename)
                )
                self.exportMenu.setEnabled(True)
                self.saveimageAction.setEnabled(True)


    def updateScene(self):
        # Reset scene
        self.scene.setFreqRange(self.sdrdatas.summaries['freq']['start'], self.sdrdatas.summaries['freq']['end'],
                                self.sdrdatas.summaries['freq']['step'])

        # Generate Heatmap image
        pixmap = self.scene.generateHeatmap(self.sdrdatas)
        self.scene.heatmap.setPixmap(pixmap)

        # Update the legend freqs
        self.scene.legend.updateLegendSize(self.jsonstations)

        # Set items positions
        self.scene.heatmap.setPos(QtCore.QPointF(0, self.scene.ruler.height()))
        self.scene.legend.setPos(QtCore.QPointF(0, self.scene.ruler.height() + self.scene.heatmap.pixmap().height()))

        # Compute the scene height
        totalheight = self.scene.ruler.height() + pixmap.height() + self.scene.legend.height()
        self.scene.setSceneRect(QtCore.QRectF(0, 0, pixmap.width(), totalheight))
        self.view.update()


def main():
    # Create main application
    app = QtGui.QApplication(sys.argv)
    mainWindow = MainWindow()

    # Load config file and get rootdir
    config = commons.loadConfigFile(commons.getJSONConfigFilename(), None)
    mainWindow.rootdir = os.path.dirname(os.path.realpath(__file__))
    if 'rootdir' in config['global']:
        mainWindow.rootdir = config['global']['rootdir']

    # Resize and launch application
    mainWindow.setGeometry(100, 100, 800, 500)
    mainWindow.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()