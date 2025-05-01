import sys
import os
from PyQt5 import QtWidgets, QtCore
import subprocess
import cv2

class AudioMergerGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("180Kino Audio Merger")
        self.init_ui()

    def init_ui(self):
        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)

        form = QtWidgets.QFormLayout()
        self.left_path = QtWidgets.QLineEdit(); btn = QtWidgets.QPushButton("Load Left Video")
        btn.clicked.connect(lambda: self.load_video(self.left_path, self.left_start, self.left_end))
        form.addRow(btn, self.left_path)

        self.left_start = QtWidgets.QSpinBox(); self.left_end = QtWidgets.QSpinBox()
        self.left_end_checkbox = QtWidgets.QCheckBox("Until end")
        self.left_end_checkbox.setChecked(True)
        self.left_end_checkbox.stateChanged.connect(self.toggle_left_end)
        h1 = QtWidgets.QHBoxLayout(); h1.addWidget(QtWidgets.QLabel("Start frame:")); h1.addWidget(self.left_start);
        h1.addWidget(QtWidgets.QLabel("End frame:")); h1.addWidget(self.left_end); h1.addWidget(self.left_end_checkbox)
        form.addRow(h1)

        self.right_path = QtWidgets.QLineEdit(); btn2 = QtWidgets.QPushButton("Load Right Video")
        btn2.clicked.connect(lambda: self.load_video(self.right_path, self.right_start, self.right_end))
        form.addRow(btn2, self.right_path)

        self.right_start = QtWidgets.QSpinBox(); self.right_end = QtWidgets.QSpinBox()
        self.right_end_checkbox = QtWidgets.QCheckBox("Until end")
        self.right_end_checkbox.setChecked(True)
        self.right_end_checkbox.stateChanged.connect(self.toggle_right_end)
        h2 = QtWidgets.QHBoxLayout(); h2.addWidget(QtWidgets.QLabel("Start frame:")); h2.addWidget(self.right_start);
        h2.addWidget(QtWidgets.QLabel("End frame:")); h2.addWidget(self.right_end); h2.addWidget(self.right_end_checkbox)
        form.addRow(h2)

        self.target_path = QtWidgets.QLineEdit(); btn3 = QtWidgets.QPushButton("Load Target Video")
        btn3.clicked.connect(lambda: self.load_target(self.target_path))
        form.addRow(btn3, self.target_path)

        layout.addLayout(form)

        # mode selection
        mode_grp = QtWidgets.QGroupBox("Mode")
        mode_layout = QtWidgets.QVBoxLayout(mode_grp)
        self.mode_left = QtWidgets.QRadioButton("Use stereo audio from left video")
        self.mode_right = QtWidgets.QRadioButton("Use stereo audio from right video")
        self.mode_mix = QtWidgets.QRadioButton("Mix monos from left+right into stereo")
        self.mode_left.setChecked(True)
        mode_layout.addWidget(self.mode_left)
        mode_layout.addWidget(self.mode_right)
        mode_layout.addWidget(self.mode_mix)
        layout.addWidget(mode_grp)

        out_layout = QtWidgets.QHBoxLayout()
        self.out_path = QtWidgets.QLineEdit()
        btn_out = QtWidgets.QPushButton("Save As...")
        btn_out.clicked.connect(self.save_output)
        out_layout.addWidget(self.out_path); out_layout.addWidget(btn_out)
        layout.addLayout(out_layout)

        self.btn_merge = QtWidgets.QPushButton("Merge Audio")
        self.btn_merge.clicked.connect(self.merge_audio)
        layout.addWidget(self.btn_merge)

        self.progress = QtWidgets.QProgressBar()
        layout.addWidget(self.progress)

        self.setCentralWidget(central)

    def load_video(self, lineedit, start_sb, end_sb):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load Video", filter="Videos (*.mp4 *.mov *.mkv)")
        if path:
            lineedit.setText(path)
            cap = cv2.VideoCapture(path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            start_sb.setRange(0, frames-1)
            end_sb.setRange(0, frames-1)
            start_sb.setValue(0)
            end_sb.setValue(frames)
            if lineedit is self.left_path:
                self.left_fps = fps; self.left_frames = frames
            else:
                self.right_fps = fps; self.right_frames = frames

    def toggle_left_end(self, state):
        self.left_end.setEnabled(not state)

    def toggle_right_end(self, state):
        self.right_end.setEnabled(not state)

    def load_target(self, lineedit):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load Target Video", filter="Videos (*.mp4)")
        if path:
            lineedit.setText(path)

    def save_output(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Output Video", filter="MP4 Video (*.mp4)")
        if path:
            self.out_path.setText(path)

    def merge_audio(self):
        left = self.left_path.text(); right = self.right_path.text(); target = self.target_path.text()
        out = self.out_path.text()
        if not all([left, right, target, out]):
            QtWidgets.QMessageBox.warning(self, "Error", "Please fill all file paths.")
            return
        ls = self.left_start.value(); le = None if self.left_end_checkbox.isChecked() else self.left_end.value()
        rs = self.right_start.value(); re = None if self.right_end_checkbox.isChecked() else self.right_end.value()
        if self.mode_left.isChecked():
            cmd = ["ffmpeg", "-y"]
            if ls: cmd += ["-ss", str(ls/self.left_fps)]
            if le: cmd += ["-to", str(le/self.left_fps)]
            cmd += ["-i", left, "-i", target, "-map", "1:v", "-map", "0:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out]
        elif self.mode_right.isChecked():
            cmd = ["ffmpeg", "-y"]
            if rs: cmd += ["-ss", str(rs/self.right_fps)]
            if re: cmd += ["-to", str(re/self.right_fps)]
            cmd += ["-i", right, "-i", target, "-map", "1:v", "-map", "0:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out]
        else:
            complex_filter = (
                f"[0:a]atrim=start={ls/fps}:end={le/fps if le else ''},asetpts=PTS-STARTPTS[a0];"
                f"[1:a]atrim=start={rs/self.right_fps}:end={re/self.right_fps if re else ''},asetpts=PTS-STARTPTS[a1];"
                "[a0][a1]join=inputs=2:channel_layout=stereo[a]"
            )
            cmd = ["ffmpeg", "-y"]
            if ls: cmd += ["-ss", str(ls/self.left_fps)]
            if le: cmd += ["-to", str(le/self.left_fps)]
            cmd += ["-i", left]
            if rs: cmd += ["-ss", str(rs/self.right_fps)]
            if re: cmd += ["-to", str(re/self.right_fps)]
            cmd += ["-i", right, "-i", target, "-filter_complex", complex_filter,
                    "-map", "2:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out]

        self.progress.setValue(0)
        self.proc = QtCore.QProcess(self)
        self.proc.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self.handle_progress)
        self.proc.finished.connect(self.finish)
        self.proc.start(cmd[0], cmd[1:])

    def handle_progress(self):
        text = bytes(self.proc.readAllStandardOutput()).decode()
        for line in text.splitlines():
            if line.startswith('out_time_ms='):
                ot = int(line.split('=')[1])
                # estimate percent (assume left duration)
                total = int(self.left_frames / self.left_fps * 1000)
                pct = int(ot / total * 100)
                self.progress.setValue(min(pct, 100))

    def finish(self, exitCode, exitStatus):
        if exitCode != 0:
            stderr = bytes(self.proc.readAllStandardOutput()).decode()
            QtWidgets.QMessageBox.critical(self, "FFmpeg Error", stderr)
        else:
            self.progress.setValue(100)
            QtWidgets.QMessageBox.information(self, "Done", "Audio merged successfully.")

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = AudioMergerGUI()
    w.show()
    sys.exit(app.exec_())
