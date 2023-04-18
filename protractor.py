#!/usr/bin/env python3

# Copyright (c) 2023 Fritz Webering
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import math
from PyQt5.Qt import Qt, QApplication, QGuiApplication, QObject, QWidget, QRegion
from PyQt5.QtCore import QPoint, QPointF, QRect, QRectF, QSize, pyqtSignal
from PyQt5.QtGui import QPainter, QPen
from PyQt5.QtGui import QImage, QPixmap, QColor, QBitmap
from PyQt5.QtWidgets import QLabel


def threePointAngle(p1: QPoint, center: QPoint, p2: QPoint):
    d1 = p1 - center
    d2 = p2 - center
    dot = d1.x() * d2.x() + d1.y() * d2.y()      # dot product between [p1.x(), p1.y()] and [p2.x(), p2.y()]
    det = d1.x() * d2.y() - d1.y() * d2.x()      # determinant
    return math.atan2(det, dot)

def centerPoint(w: QWidget):
    return QPointF(w.x() + w.width() / 2, w.y() + w.height() / 2)

def drawShortenedLine(qPainter, p1, p2, shorten1 = 0.0, shorten2 = 0.0):
    diff = p2 - p1
    length = math.sqrt(QPointF.dotProduct(diff, diff))
    if length == 0 or shorten1 + shorten2 >= length:
        return
    p2 = p1 + diff * (1 - max(0, min(1, (shorten2 / length))))
    p1 = p1 + diff * max(0, min(1, (shorten1 / length)))
    qPainter.drawLine(p1, p2)

QPainter.drawShortenedLine = drawShortenedLine

def pointsOnLine(p1, p2, maxDistance):
    diff = p2 - p1
    countX = math.ceil(abs(p1.x() - p2.x()) / maxDistance)
    countY = math.ceil(abs(p1.y() - p2.y()) / maxDistance)
    count = max(1, min(countX, countY))
    segment = diff / count
    return [ p1 + segment * i for i in range(count) ] + [ p2 ]

def rectsOnLine(p1, p2, maxDistance, overlap):
    points = pointsOnLine(p1, p2, maxDistance)
    pairs = list(zip(points[1:], points[:-1]))
    return [ QRectF(pA, pB).normalized().adjusted(-overlap/2, -overlap/2, overlap/2, overlap/2) for pA, pB in pairs ]


class Handle(QLabel):
    moved = pyqtSignal(name='moved')

    def __init__(self, parent):
        super().__init__(parent)
        self.setGeometry(300, 300, 31, 31)
        self.setCursor(Qt.CrossCursor)
        # self.setAutoFillBackground(True)

    def r(self): return self.width() / 4

    def paintEvent(self, event):
        dark = QPen(Qt.black, 1, Qt.SolidLine)
        light = QPen(Qt.white, 2, Qt.SolidLine)
        # light = QPen(QColor(200, 220, 255), 2, Qt.SolidLine)
        # light = QPen(QColor(210, 255, 210), 2, Qt.SolidLine)
        radius = self.width()/4
        qp = QPainter()
        qp.begin(self)
        # qp.setRenderHint(QPainter.Antialiasing)
        # qp.setRenderHint(QPainter.HighQualityAntialiasing)
        r = self.r() +1
        center = QPointF(self.width()/2, self.height()/2)
        for pen in light, dark:
            qp.setPen(pen)
            qp.setRenderHint(QPainter.Antialiasing, False)
            qp.drawShortenedLine(center, QPointF(0, 0), r)
            qp.drawShortenedLine(center, QPointF(0, self.height()), r)
            qp.drawShortenedLine(center, QPointF(self.width(), self.height()), r)
            qp.drawShortenedLine(center, QPointF(self.width(), 0), r)
            qp.setRenderHint(QPainter.Antialiasing, True)
            qp.drawEllipse(QPointF(self.width()/2, self.height()/2), radius, radius)
        qp.setPen(dark)
        qp.drawPoint(self.width()//2, self.height()//2)
        qp.end()

    def mousePressEvent(self, event):
        self.offset = event.pos()
    
    def mouseMoveEvent(self, event):
        self.move(self.mapToParent(event.pos()) - self.offset)
        self.moved.emit()

class Protractor(QLabel):
    angleInvert = False

    def __init__(self, parent):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        # self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setStyleSheet("QLabel#angle { font-size: 20px; background-color: white; padding: 2px; }")
        self.setCursor(Qt.OpenHandCursor)
        self.handleC = Handle(self)
        self.handle1 = Handle(self)
        self.handle2 = Handle(self)
        self.handleC.move(50, 200)
        self.handle1.move(200, 200)
        self.handle2.move(200, 50)
        self.handleC.moved.connect(self.updateDisplay)
        self.handle1.moved.connect(self.updateDisplay)
        self.handle2.moved.connect(self.updateDisplay)
        self.label = QLabel(self)
        self.label.setObjectName("angle")
        self.label.setAutoFillBackground(True)
        self.updateDisplay()

    def mousePressEvent(self, event):
        self.setCursor(Qt.ClosedHandCursor)
        self.offset = event.pos()
        event.accept()

    def mouseMoveEvent(self, event):
        diff = event.pos() - self.offset
        for widget in self.children():
            widget.move(widget.pos() + diff)
        self.offset = event.pos()
        self.updateDisplay()
        event.accept()

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)

    def mouseDoubleClickEvent(self, event):
        self.angleInvert = not self.angleInvert
        self.updateDisplay()

    def updateDisplay(self):
        self.placeLabel()
        self.adjustSize()
        angle = threePointAngle(self.handle1.pos(), self.handleC.pos(), self.handle2.pos())
        angleDeg = 180 * angle / math.pi
        if self.angleInvert:
            angleDeg = 180 - angleDeg
        if angleDeg > 180:
            angleDeg = angleDeg - 360
        self.label.setText("%0.2f °" % angleDeg)
        self.label.adjustSize()
        self.updateMask()
        self.update()

    def adjustSize(self):
        pass
        # bounds: QRect = self.childrenRect()
        # bounds = bounds.adjusted(-100, -100, 100, 100)
        # boundsScreen = QRect(self.mapToGlobal(bounds.topLeft()), bounds.size())
        # self.handleC.move(self.handleC.pos() - bounds.topLeft())
        # self.handle1.move(self.handle1.pos() - bounds.topLeft())
        # self.handle2.move(self.handle2.pos() - bounds.topLeft())
        # self.setGeometry(boundsScreen)

    def placeLabel(self):
        self.label.move(centerPoint(self.handleC).toPoint() + QPoint(-self.label.width()//2, 30))

    def updateMask(self):
        mask = self.childrenRegion()
        line1 = rectsOnLine(centerPoint(self.handleC), centerPoint(self.handle1), 40, 5)
        line2 = rectsOnLine(centerPoint(self.handleC), centerPoint(self.handle2), 40, 5)
        for r in line1 + line2:
            mask = mask.united(r.toRect())
        self.setMask(mask)

    def paintEvent(self, event):
        dark = QPen(Qt.black, 1, Qt.SolidLine)
        light = QPen(Qt.white, 2, Qt.SolidLine)
        # light = QPen(QColor(200, 220, 255), 2, Qt.SolidLine)
        # light = QPen(QColor(210, 255, 210), 2, Qt.SolidLine)
        qp = QPainter()
        qp.begin(self)
        qp.setRenderHint(QPainter.Antialiasing)
        qp.setRenderHint(QPainter.HighQualityAntialiasing)
        for pen in light, dark: 
            qp.setPen(pen)
            drawShortenedLine(qp, centerPoint(self.handleC), centerPoint(self.handle1), self.handleC.r() + 1, self.handle1.r() + 1)
            drawShortenedLine(qp, centerPoint(self.handleC), centerPoint(self.handle2), self.handleC.r() + 1, self.handle2.r() + 1)
        qp.end()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            QApplication.quit()
        else:
            QWidget.keyPressEvent(self, event)

a = QApplication(sys.argv)

widget = Protractor(None)
widget.show()

# Negative coordinates are necessary because with (0,0) xfwm will place
# the window on the current desktop and below the task bar.
taskBarSize = 32
allScreens = QApplication.desktop().geometry()
widgetSize = allScreens.adjusted(-10, -taskBarSize, 10, taskBarSize)
widget.setGeometry(widgetSize)

a.exec()
