import sys
from PyQt5 import QtWidgets, QtCore
import cv2
import subprocess

class AudioMergerGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("easyVR180AudioSync")
        self.init_ui()

    def init_ui(self):
        central = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(central)

        # Top: Left and Right video controls
        top_layout = QtWidgets.QHBoxLayout()

        # Left video group
        left_group = QtWidgets.QGroupBox("Left Video")
        left_layout = QtWidgets.QFormLayout(left_group)
        self.left_path = QtWidgets.QLineEdit("/video_L.MP4")
        btn_left = QtWidgets.QPushButton("Load Left Video")
        btn_left.clicked.connect(lambda: self.load_video(self.left_path, "left"))
        left_layout.addRow(btn_left, self.left_path)
        self.left_start = QtWidgets.QSpinBox(); self.left_end = QtWidgets.QSpinBox()
        self.left_end.setEnabled(False)
        chk_left = QtWidgets.QCheckBox("Until end"); chk_left.setChecked(True)
        chk_left.toggled.connect(lambda s: self.left_end.setEnabled(not s))
        left_layout.addRow("Start frame:", self.left_start)
        left_layout.addRow("End frame:", self.left_end)
        left_layout.addRow(chk_left)
        top_layout.addWidget(left_group)

        # Right video group
        right_group = QtWidgets.QGroupBox("Right Video")
        right_layout = QtWidgets.QFormLayout(right_group)
        self.right_path = QtWidgets.QLineEdit("/video_R.MP4")
        btn_right = QtWidgets.QPushButton("Load Right Video")
        btn_right.clicked.connect(lambda: self.load_video(self.right_path, "right"))
        right_layout.addRow(btn_right, self.right_path)
        self.right_start = QtWidgets.QSpinBox(); self.right_end = QtWidgets.QSpinBox()
        self.right_end.setEnabled(False)
        chk_right = QtWidgets.QCheckBox("Until end"); chk_right.setChecked(True)
        chk_right.toggled.connect(lambda s: self.right_end.setEnabled(not s))
        right_layout.addRow("Start frame:", self.right_start)
        right_layout.addRow("End frame:", self.right_end)
        right_layout.addRow(chk_right)
        top_layout.addWidget(right_group)

        main_layout.addLayout(top_layout)

        # Target video group
        target_group = QtWidgets.QGroupBox("Target Video (VR180 output)")
        target_layout = QtWidgets.QHBoxLayout(target_group)
        self.target_path = QtWidgets.QLineEdit("/target_LR.MP4")
        btn_target = QtWidgets.QPushButton("Load Target Video")
        btn_target.clicked.connect(lambda: self.load_file(self.target_path, "Videos (*.mp4)", "Load Target Video"))
        target_layout.addWidget(btn_target); target_layout.addWidget(self.target_path)
        main_layout.addWidget(target_group)

        # Mode selection
        mode_group = QtWidgets.QGroupBox("Mode")
        mode_layout = QtWidgets.QVBoxLayout(mode_group)
        self.mode_left = QtWidgets.QRadioButton("Use stereo audio from left video")
        self.mode_right = QtWidgets.QRadioButton("Use stereo audio from right video")
        self.mode_mix = QtWidgets.QRadioButton("Mix monos from left+right into stereo")
        self.mode_left.setChecked(True)
        for w in (self.mode_left, self.mode_right, self.mode_mix):
            w.toggled.connect(self.update_output_filename)
            mode_layout.addWidget(w)
        main_layout.addWidget(mode_group)

        # Output file
        out_group = QtWidgets.QGroupBox("Output File")
        out_layout = QtWidgets.QHBoxLayout(out_group)
        self.out_path = QtWidgets.QLineEdit()
        btn_out = QtWidgets.QPushButton("Save As...")
        btn_out.clicked.connect(lambda: self.load_file(self.out_path, "MP4 Video (*.mp4)", "Save Output Video"))
        out_layout.addWidget(btn_out); out_layout.addWidget(self.out_path)
        main_layout.addWidget(out_group)

        # Update default output
        self.update_output_filename()

        # Merge button and progress
        self.btn_merge = QtWidgets.QPushButton("Merge Audio")
        self.btn_merge.clicked.connect(self.merge_audio)
        self.progress = QtWidgets.QProgressBar()
        main_layout.addWidget(self.btn_merge)
        main_layout.addWidget(self.progress)

        self.setCentralWidget(central)

    def load_video(self, lineedit, side):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, f"Load {side.capitalize()} Video", filter="Videos (*.mp4 *.mov *.mkv)")
        if path:
            lineedit.setText(path)
            cap = cv2.VideoCapture(path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            sb = getattr(self, f"{side}_start"); eb = getattr(self, f"{side}_end"); chk = eb.isEnabled()
            sb.setRange(0, frames-1); eb.setRange(0, frames-1)

    def load_file(self, lineedit, filter, title):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, title, filter=filter)
        if path: lineedit.setText(path)

    def update_output_filename(self):
        tag = 'L' if self.mode_left.isChecked() else 'R' if self.mode_right.isChecked() else 'M'
        self.out_path.setText(f"output_LR_wAudio{tag}.mp4")

    def merge_audio(self):
        left, right, target, out = self.left_path.text(), self.right_path.text(), self.target_path.text(), self.out_path.text()
        if not all([left, right, target, out]):
            QtWidgets.QMessageBox.warning(self, "Error", "Please fill all paths.")
            return
        ls, le = self.left_start.value(), None if not self.left_end.isEnabled() else self.left_end.value()
        rs, re = self.right_start.value(), None if not self.right_end.isEnabled() else self.right_end.value()
        cmd = ["ffmpeg", "-y"]
        if self.mode_left.isChecked():
            if ls: cmd += ["-ss", str(ls/self.get_fps(left))]
            if le: cmd += ["-to", str(le/self.get_fps(left))]
            cmd += ["-i", left, "-i", target, "-map", "1:v", "-map", "0:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out]
        elif self.mode_right.isChecked():
            if rs: cmd += ["-ss", str(rs/self.get_fps(right))]
            if re: cmd += ["-to", str(re/self.get_fps(right))]
            cmd += ["-i", right, "-i", target, "-map", "1:v", "-map", "0:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out]
        else:
            fps_l = self.get_fps(left); fps_r = self.get_fps(right)
            filt = (f"[0:a]atrim=start={ls/fps_l}:end={le/fps_l if le else ''},asetpts=PTS-STARTPTS[a0];"
                    f"[1:a]atrim=start={rs/fps_r}:end={re/fps_r if re else ''},asetpts=PTS-STARTPTS[a1];"
                    "[a0][a1]join=inputs=2:channel_layout=stereo[a]")
            cmd += ["-i", left]
            cmd += ["-i", right]
            cmd += ["-i", target, "-filter_complex", filt, "-map", "2:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out]
        self.progress.setValue(0)
        self.proc = QtCore.QProcess(self)
        self.proc.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self.handle_progress)
        self.proc.finished.connect(self.finish)
        self.proc.start(cmd[0], cmd[1:])

    def get_fps(self, path):
        cap = cv2.VideoCapture(path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        return fps

    def handle_progress(self):
        text = bytes(self.proc.readAllStandardOutput()).decode()
        for line in text.splitlines():
            if line.startswith('out_time_ms='):
                ot = int(line.split('=')[1])
                total = int(self.get_fps(self.left_path.text()) * (self.left_end.value() or 0) * 1000)
                pct = int(ot / total * 100) if total else 0
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
