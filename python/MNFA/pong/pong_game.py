# pong_game.py

import nuke
import nukescripts
from PySide2 import QtWidgets, QtCore, QtGui
import os
import random

# Module-level variable to hold the panel instance
pong_game_panel_instance = None

class PongGamePanel(QtWidgets.QWidget):
    def __init__(self):
        super(PongGamePanel, self).__init__()
        self.setWindowTitle("Pong Game")
        self.setMinimumSize(400, 350)  # Optional: set a minimum size

        # Game variables
        self.ball_radius_ratio = 0.015  # Ball radius as a percentage of width
        self.ball_x = self.width() / 2
        self.ball_y = (self.height() - 100) / 2  # Adjusted for controls
        self.ball_dx = 4  # Horizontal velocity (adjusted dynamically)
        self.ball_dy = 3  # Vertical velocity (adjusted dynamically)

        # Paddle variables
        self.paddle_width_ratio = 0.0125  # Paddle width as a percentage of width
        self.paddle_height_ratio = 0.12  # Paddle height as a percentage of height
        self.paddle_speed_ratio = 0.00625  # Paddle speed as a percentage of height

        # Initial paddle positions (will be updated in update_game_dimensions)
        self.paddle1_x = 0
        self.paddle1_y = 0
        self.paddle2_x = 0
        self.paddle2_y = 0

        # AI paddle speed factor (less than 1 to make it slower than the player)
        self.ai_speed_factor = 1.4  # AI paddle moves at 90% of player's paddle speed

        # AI reaction time (increase to make AI react slower)
        self.ai_reaction_time = 20  # AI reacts every 30ms

        # AI paddle speed (will be set in update_game_dimensions)
        self.ai_paddle_speed = 0

        # Movement timers for continuous movement
        self.paddle1_up_timer = QtCore.QTimer()
        self.paddle1_down_timer = QtCore.QTimer()

        # Game loop timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_game)
        self.timer.start(16)  # Start the timer immediately

        # Countdown variables
        self.countdown = 3
        self.countdown_active = False  # Start inactive until game starts

        # Countdown timer
        self.countdown_timer = QtCore.QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)

        # Score variables
        self.score_player1 = 0
        self.score_player2 = 0
        self.winning_score = 5  # First to 5 points wins

        # Game state
        self.game_started = False
        self.game_paused = False
        self.winner = None

        # Confetti particles
        self.confetti_particles = []

        # Set focus policy to receive keyboard events
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        # Load assets
        self.load_ball_image()

        # Create control buttons and instructions
        self.create_controls()

        # AI reaction delay
        self.ai_reaction_timer = QtCore.QTimer()
        self.ai_reaction_timer.timeout.connect(self.update_ai_paddle)
        self.ai_reaction_timer.start(self.ai_reaction_time)

        # Initialize game dimensions
        self.update_game_dimensions()

    def update_game_dimensions(self):
        # Update game dimensions
        self.game_width = self.width()
        self.game_height = self.height() - 100  # Reserve space for controls

        # Update paddle dimensions
        self.paddle_width = self.game_width * self.paddle_width_ratio
        self.paddle_height = self.game_height * self.paddle_height_ratio
        self.paddle_speed = self.game_height * self.paddle_speed_ratio

        # Update AI paddle speed
        self.ai_paddle_speed = self.paddle_speed * self.ai_speed_factor

        # Update ball radius
        self.ball_radius = self.game_width * self.ball_radius_ratio

        # Update initial paddle positions
        self.paddle1_x = self.game_width * 0.05  # 5% from the left
        self.paddle2_x = self.game_width * 0.95 - self.paddle_width  # 5% from the right

        if not self.game_started:
            # Center paddles and ball
            self.paddle1_y = (self.game_height - self.paddle_height) / 2
            self.paddle2_y = (self.game_height - self.paddle_height) / 2
            self.ball_x = self.game_width / 2
            self.ball_y = self.game_height / 2

        # Update ball velocities based on size
        self.ball_dx = self.game_width * 0.005  # Adjusted for panel size
        self.ball_dy = self.game_height * 0.005  # Adjusted for panel size

        # Ensure the ball velocity is not zero
        if self.ball_dx == 0:
            self.ball_dx = 1
        if self.ball_dy == 0:
            self.ball_dy = 1

    def load_ball_image(self):
        # Adjust the path to the image
        script_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(script_dir, 'nuke_logo.png')
        self.ball_image = QtGui.QPixmap(image_path)
        if self.ball_image.isNull():
            print('Error: Ball image not found at', image_path)
            self.ball_image = None

    def create_controls(self):
        # Create a container widget for controls
        self.controls_widget = QtWidgets.QWidget(self)
        # Adjusted position to be within the visible area
        self.controls_widget.setGeometry(0, self.height() - 100, self.width(), 100)

        # Instructions label
        instructions_text = (
            "Instructions:\n"
            "- Use the Up and Down arrow keys to move your paddle.\n"
            "- Press 'Start' to begin the game.\n"
            "- Press 'Pause' to pause/resume the game.\n"
            "- Press 'Stop' to stop and reset the game."
        )
        self.instructions_label = QtWidgets.QLabel(instructions_text, self.controls_widget)
        self.instructions_label.setGeometry(20, 0, self.width() - 40, 60)  # Added padding
        self.instructions_label.setStyleSheet("color: white;")
        self.instructions_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        # Start, Pause, Stop buttons
        self.start_button = QtWidgets.QPushButton("Start", self.controls_widget)
        self.start_button.setGeometry(10, 70, 60, 30)
        self.start_button.clicked.connect(self.start_game)

        self.pause_button = QtWidgets.QPushButton("Pause", self.controls_widget)
        self.pause_button.setGeometry(80, 70, 60, 30)
        self.pause_button.clicked.connect(self.pause_game)

        self.stop_button = QtWidgets.QPushButton("Stop", self.controls_widget)
        self.stop_button.setGeometry(150, 70, 60, 30)
        self.stop_button.clicked.connect(self.stop_game)

    # Paddle movement methods with continuous movement
    def move_paddle1_up_start(self):
        self.paddle1_up_timer.timeout.connect(self.move_paddle1_up)
        self.paddle1_up_timer.start(16)

    def move_paddle1_up_stop(self):
        self.paddle1_up_timer.stop()
        self.paddle1_up_timer.timeout.disconnect(self.move_paddle1_up)

    def move_paddle1_down_start(self):
        self.paddle1_down_timer.timeout.connect(self.move_paddle1_down)
        self.paddle1_down_timer.start(16)

    def move_paddle1_down_stop(self):
        self.paddle1_down_timer.stop()
        self.paddle1_down_timer.timeout.disconnect(self.move_paddle1_down)

    # Paddle movement methods
    def move_paddle1_up(self):
        self.paddle1_y -= self.paddle_speed
        if self.paddle1_y < 0:
            self.paddle1_y = 0

    def move_paddle1_down(self):
        self.paddle1_y += self.paddle_speed
        if self.paddle1_y + self.paddle_height > self.game_height:
            self.paddle1_y = self.game_height - self.paddle_height

    def update_countdown(self):
        if not self.game_started:
            return  # Do not update countdown if game hasn't started
        if self.countdown > 1:
            self.countdown -= 1
        else:
            self.countdown_active = False
            self.countdown_timer.stop()
            # The game loop timer is already running
        self.update()  # Redraw to update the countdown display

    def update_game(self):
        if self.countdown_active or self.game_paused:
            return  # Do not update the game until countdown is over or if paused

        if self.winner:
            self.update_confetti()
            self.update()
            return

        if not self.game_started:
            return

        # Update the ball's position
        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy

        # Ball collision with top and bottom walls
        if self.ball_y - self.ball_radius <= 0 or self.ball_y + self.ball_radius >= self.game_height:
            self.ball_dy *= -1  # Reverse vertical direction

        # Ball collision with Compositor's paddle
        if self.ball_x - self.ball_radius <= self.paddle1_x + self.paddle_width:
            if self.paddle1_y <= self.ball_y <= self.paddle1_y + self.paddle_height:
                self.ball_dx *= -1  # Reverse horizontal direction
                self.ball_x = self.paddle1_x + self.paddle_width + self.ball_radius  # Prevent sticking
            else:
                # Ball missed paddle 1
                self.score_player2 += 1
                self.check_winner()
                if not self.winner:
                    self.reset_round()

        # Ball collision with Computer's paddle
        elif self.ball_x + self.ball_radius >= self.paddle2_x:
            if self.paddle2_y <= self.ball_y <= self.paddle2_y + self.paddle_height:
                self.ball_dx *= -1  # Reverse horizontal direction
                self.ball_x = self.paddle2_x - self.ball_radius  # Prevent sticking
            else:
                # Ball missed paddle 2
                self.score_player1 += 1
                self.check_winner()
                if not self.winner:
                    self.reset_round()

        self.update()  # Redraw the widget

    def update_ai_paddle(self):
        if not self.game_started or self.game_paused or self.winner:
            return
        # Update AI paddle (Computer)
        self.move_ai_paddle()

    def move_ai_paddle(self):
        # Simple AI to follow the ball with some limitations
        # AI paddle moves only if the ball is moving towards it
        if self.ball_dx > 0:
            # Introduce randomness to AI decision
            if QtCore.QRandomGenerator.global_().bounded(100) < 90:  # Reduced from 95% to 90%
                if self.paddle2_y + self.paddle_height / 2 < self.ball_y:
                    self.paddle2_y += self.ai_paddle_speed
                elif self.paddle2_y + self.paddle_height / 2 > self.ball_y:
                    self.paddle2_y -= self.ai_paddle_speed
            else:
                # AI makes a mistake and does not move
                pass

            # Ensure the paddle stays within the game area
            if self.paddle2_y < 0:
                self.paddle2_y = 0
            elif self.paddle2_y + self.paddle_height > self.game_height:
                self.paddle2_y = self.game_height - self.paddle_height

    def check_winner(self):
        if self.score_player1 >= self.winning_score:
            self.game_over(winner='Compositor')
        elif self.score_player2 >= self.winning_score:
            self.game_over(winner='Computer')

    def game_over(self, winner):
        self.game_started = False
        self.game_paused = False
        self.countdown_timer.stop()
        self.countdown_active = False
        self.pause_button.setText("Pause")
        self.winner = winner
        self.start_confetti()
        self.update()

    def start_confetti(self):
        # Generate confetti particles
        self.confetti_particles = []
        colors = ['#FF69B4', '#1E90FF', '#32CD32', '#FFD700', '#FF4500']
        for _ in range(200):
            particle = {
                'x': random.uniform(0, self.width()),
                'y': random.uniform(-self.game_height, 0),
                'vx': random.uniform(-1, 1),
                'vy': random.uniform(2, 5),
                'size': random.uniform(5, 10),
                'color': random.choice(colors),
                'life': random.randint(50, 100)
            }
            self.confetti_particles.append(particle)

    def update_confetti(self):
        for particle in self.confetti_particles[:]:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['life'] -= 1
            if particle['life'] <= 0 or particle['y'] > self.game_height:
                self.confetti_particles.remove(particle)

    def reset_round(self):
        # Reset ball to center
        self.ball_x = self.game_width / 2
        self.ball_y = self.game_height / 2
        # Reverse ball direction
        self.ball_dx *= -1
        # Reset countdown
        self.countdown = 3
        self.countdown_active = True
        self.countdown_timer.start(1000)  # Restart countdown timer
        self.update()

    def start_game(self):
        self.game_started = True
        self.game_paused = False
        self.winner = None
        self.confetti_particles = []
        self.countdown_active = True
        self.countdown = 3
        self.countdown_timer.start(1000)
        self.update()

    def pause_game(self):
        if not self.game_started or self.winner:
            return  # Can't pause if the game hasn't started or game is over
        if self.game_paused:
            # Resume the game
            self.game_paused = False
            self.pause_button.setText("Pause")
        else:
            # Pause the game
            self.game_paused = True
            self.pause_button.setText("Resume")
        self.update()

    def stop_game(self):
        self.game_started = False
        self.game_paused = False
        self.winner = None
        self.countdown_timer.stop()
        self.countdown_active = False
        self.countdown = 3
        self.pause_button.setText("Pause")
        # Reset scores
        self.score_player1 = 0
        self.score_player2 = 0
        # Reset paddles
        self.paddle1_y = (self.game_height - self.paddle_height) / 2
        self.paddle2_y = (self.game_height - self.paddle_height) / 2
        # Reset ball
        self.ball_x = self.game_width / 2
        self.ball_y = self.game_height / 2
        # Clear confetti
        self.confetti_particles = []
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        # Enable anti-aliasing for smoother edges
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Clear the background
        painter.fillRect(0, 0, self.width(), self.game_height, QtGui.QColor(0, 0, 0))  # Black background

        # Draw the center line
        pen = QtGui.QPen(QtGui.QColor(255, 255, 255))
        pen.setStyle(QtCore.Qt.DashLine)
        painter.setPen(pen)
        painter.drawLine(self.width() / 2, 0, self.width() / 2, self.game_height)

        # Draw paddles
        painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))  # White color
        painter.setPen(QtCore.Qt.NoPen)
        # Compositor's paddle
        painter.drawRect(self.paddle1_x, self.paddle1_y, self.paddle_width, self.paddle_height)
        # Computer's paddle
        painter.drawRect(self.paddle2_x, self.paddle2_y, self.paddle_width, self.paddle_height)

        # Draw rotated labels on the sides
        painter.setPen(QtGui.QColor(255, 255, 255))  # White color
        font_size = max(int(self.width() * 0.03), 12)
        font = QtGui.QFont('Arial', font_size)
        painter.setFont(font)

        # Calculate text dimensions
        text_width = self.game_height
        text_height = font_size * 2  # Approximate height

        # Draw "Compositor" on the left side
        painter.save()
        painter.translate(self.paddle1_x + self.paddle_width + font_size, self.game_height / 2)
        painter.rotate(-90)
        text_rect = QtCore.QRectF(-text_width / 2, -text_height / 2, text_width, text_height)
        painter.drawText(text_rect, QtCore.Qt.AlignCenter, "Compositor")
        painter.restore()

        # Draw "Computer" on the right side
        painter.save()
        painter.translate(self.paddle2_x - font_size, self.game_height / 2)
        painter.rotate(90)
        text_rect = QtCore.QRectF(-text_width / 2, -text_height / 2, text_width, text_height)
        painter.drawText(text_rect, QtCore.Qt.AlignCenter, "Computer")
        painter.restore()

        # Draw the ball
        if not self.countdown_active and self.game_started and not self.game_paused:
            if self.ball_image:
                # Scale the ball image to match the new ball radius
                scaled_ball_image = self.ball_image.scaled(
                    self.ball_radius * 2, self.ball_radius * 2,
                    QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
                )
                # Draw the scaled ball image
                ball_rect = scaled_ball_image.rect()
                ball_rect.moveCenter(QtCore.QPoint(int(self.ball_x), int(self.ball_y)))
                painter.drawPixmap(ball_rect, scaled_ball_image)
            else:
                # Fallback to drawing a circle if image not loaded
                painter.setBrush(QtGui.QBrush(QtGui.QColor('#fdc842')))  # Nuke orange color
                painter.drawEllipse(QtCore.QPointF(self.ball_x, self.ball_y), self.ball_radius, self.ball_radius)

        # Draw the scores
        painter.setPen(QtGui.QColor(255, 255, 255))  # White color
        font_size = max(int(self.width() * 0.03), 12)
        font = QtGui.QFont('Arial', font_size, QtGui.QFont.Bold)
        painter.setFont(font)
        score_text = f"{int(self.score_player1)}    Score    {int(self.score_player2)}"
        text_rect = QtCore.QRectF(0, 0, self.width(), font_size * 2)
        painter.drawText(text_rect, QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter, score_text)

        # Draw the countdown
        if self.countdown_active and self.game_started:
            painter.setPen(QtGui.QColor(255, 255, 255))  # White color
            font_size = max(int(self.width() * 0.06), 24)
            font = QtGui.QFont('Arial', font_size, QtGui.QFont.Bold)
            painter.setFont(font)
            text = str(self.countdown)
            text_rect = QtCore.QRectF(0, 0, self.width(), self.game_height)
            painter.drawText(text_rect, QtCore.Qt.AlignCenter, text)

        # Draw paused text
        if self.game_paused:
            painter.setPen(QtGui.QColor(255, 255, 255))  # White color
            font_size = max(int(self.width() * 0.06), 24)
            font = QtGui.QFont('Arial', font_size, QtGui.QFont.Bold)
            painter.setFont(font)
            text = "Paused"
            text_rect = QtCore.QRectF(0, 0, self.width(), self.game_height)
            painter.drawText(text_rect, QtCore.Qt.AlignCenter, text)

        # Draw winner text and confetti
        if self.winner:
            # Draw winner text
            painter.setPen(QtGui.QColor(255, 215, 0))  # Gold color
            font_size = max(int(self.width() * 0.06), 24)
            font = QtGui.QFont('Arial', font_size, QtGui.QFont.Bold)
            painter.setFont(font)
            text = f"{self.winner} Wins!"
            text_rect = QtCore.QRectF(0, 0, self.width(), self.game_height / 2)
            painter.drawText(text_rect, QtCore.Qt.AlignCenter, text)

            # Draw confetti particles
            for particle in self.confetti_particles:
                color = QtGui.QColor(particle['color'])
                painter.setPen(QtCore.Qt.NoPen)
                painter.setBrush(color)
                painter.drawEllipse(particle['x'], particle['y'], particle['size'], particle['size'])

        # Draw game over text if game is stopped and no winner
        if not self.game_started and not self.countdown_active and not self.winner:
            painter.setPen(QtGui.QColor(255, 255, 255))  # White color
            font_size = max(int(self.width() * 0.045), 18)
            font = QtGui.QFont('Arial', font_size, QtGui.QFont.Bold)
            painter.setFont(font)
            text = "Press 'Start' to Begin"
            text_rect = QtCore.QRectF(0, 0, self.width(), self.game_height)
            painter.drawText(text_rect, QtCore.Qt.AlignCenter, text)

        painter.end()

    def resizeEvent(self, event):
        super(PongGamePanel, self).resizeEvent(event)
        # Update positions of control buttons on resize
        self.controls_widget.setGeometry(0, self.height() - 100, self.width(), 100)
        self.instructions_label.setGeometry(20, 0, self.width() - 40, 60)  # Added padding
        self.start_button.move(10, 70)
        self.pause_button.move(80, 70)
        self.stop_button.move(150, 70)

        # Update game dimensions
        self.update_game_dimensions()

    # Implement keyboard controls for Compositor
    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Up:
            self.move_paddle1_up_start()
        elif key == QtCore.Qt.Key_Down:
            self.move_paddle1_down_start()

    def keyReleaseEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Up:
            self.move_paddle1_up_stop()
        elif key == QtCore.Qt.Key_Down:
            self.move_paddle1_down_stop()

        # Ensure the parent class also processes the events
        super(PongGamePanel, self).keyReleaseEvent(event)

    def focusInEvent(self, event):
        # Ensure the widget accepts focus to receive keyboard events
        super(PongGamePanel, self).focusInEvent(event)

# Corrected show_pong_game_panel function
def show_pong_game_panel():
    global pong_game_panel_instance  # Declare as global to persist the reference
    # Create an instance of the PongGamePanel
    pong_game_panel_instance = PongGamePanel()
    # Register the panel
    panel = nukescripts.panels.registerWidgetAsPanel(
        'pong_game.PongGamePanel',  # Full module path to the class
        'Pong Game',
        'uk.co.yourname.PongGamePanel',
        True
    )
    # Add the panel to a Nuke pane
    pane = nuke.getPaneFor('Properties.1')
    if not pane:
        pane = nuke.getPaneFor('DAG.1')
    panelInstance = panel.addToPane(pane)
