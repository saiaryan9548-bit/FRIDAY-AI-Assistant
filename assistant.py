"""
FRIDAY ASSISTANT
Central controller for voice, AI, memory, skills, system and web controls.
"""

import time
import re

from .listener import Listener
from .speaker import Speaker
from .command_parser import parse
from .launcher import open_item

from intent_parser import IntentParser
from media_control import MediaControl
from system_control import SystemControl
from system_monitor import SystemMonitor
from skills.files.file_control import FileControl
from window_control import WindowControl
from web_control import WebControl
from clipboard_control import ClipboardControl
from input_control import InputControl
from developer_control import DeveloperControl

from ai_brain import AIBrain
from agent_core import AgentCore
from memory import Memory
from context_memory import ContextMemory
from friday.permission_manager import PermissionManager

# Skill system
from skills import SkillManager
from skills.system import SystemSkill
from skills.vision import VisionSkill
from skills.browser import BrowserSkill
from skills.files import FileSkill


class Assistant:

    def __init__(self, gui=None):

        self.gui = gui

        self.running = False
        self.awake = False

        print("Initializing FRIDAY...")

        # =====================================================
        # CORE SYSTEMS
        # =====================================================

        self.listener = Listener()
        self.speaker = Speaker()

        self.intent = IntentParser()

        self.media = MediaControl()
        self.system = SystemControl()
        self.monitor = SystemMonitor()
        self.files = FileControl()
        self.windows = WindowControl()
        self.web = WebControl()
        self.clipboard = ClipboardControl()
        self.input = InputControl()
        self.developer = DeveloperControl()

        # =====================================================
        # AI
        # =====================================================

        self.ai = AIBrain()
        self.agent = AgentCore(self)

        # =====================================================
        # MEMORY
        # =====================================================

        self.memory = Memory()
        self.context = ContextMemory()
        self.permissions = PermissionManager()

        # =====================================================
        # SKILL SYSTEM
        # =====================================================

        self.skills = SkillManager(self)

        # Register System Skill
        self.skills.register(
            SystemSkill(self)
        )

        # Register Vision Skill
        self.skills.register(
            VisionSkill(self)
        )

        # Register Browser Skill
        self.skills.register(
            BrowserSkill(self)
        )

        # Register File Skill
        self.skills.register(
            FileSkill(self)
        )

        print(
            self.skills.status()
        )

        print("FRIDAY ready.")

    # ==========================================================
    # GUI
    # ==========================================================

    def set_gui_status(self, mode, info=None):

        if not self.gui:
            return

        try:

            self.gui.app.after(
                0,
                lambda: self.gui.set_mode(mode)
            )

            if info:

                self.gui.app.after(
                    0,
                    lambda: self.gui.set_info(info)
                )

        except Exception:
            pass

    def gui_log(self, message):

        if not self.gui:
            return

        try:

            self.gui.app.after(
                0,
                lambda: self.gui.add_log(message)
            )

        except Exception:
            pass

    # ==========================================================
    # WAKE WORD
    # ==========================================================

    def check_wake_word(self, text):

        text = text.lower().strip()

        wake_words = (
            "friday",
            "hello friday",
            "hey friday",
            "hi friday",
            "ok friday",
            "okay friday",
        )

        for wake in wake_words:

            if text == wake:
                return True, ""

            if text.startswith(
                wake + " "
            ):

                command = text[
                    len(wake):
                ].strip()

                return True, command

        return False, None

    # ==========================================================
    # MAIN LOOP
    # ==========================================================

    def run(self):

        self.running = True
        self.awake = False

        self.set_gui_status(
            "STANDBY",
            "Say 'Hello FRIDAY' to wake me."
        )

        self.gui_log(
            "[SYSTEM] FRIDAY is standing by."
        )

        while self.running:

            if not self.awake:

                self.set_gui_status(
                    "STANDBY",
                    "Say 'Hello FRIDAY' to wake me."
                )

            else:

                self.set_gui_status(
                    "LISTENING",
                    "Listening for your command..."
                )

            heard = self.listener.listen()

            if not heard:
                continue

            self.gui_log(
                f"YOU: {heard}"
            )

            # =================================================
            # WAKE WORD
            # =================================================

            if not self.awake:

                woke, command_after_wake = (
                    self.check_wake_word(heard)
                )

                if not woke:
                    continue

                self.awake = True

                self.set_gui_status(
                    "AWAKE",
                    "FRIDAY is ready."
                )

                self.gui_log(
                    "[SYSTEM] Wake word detected."
                )

                if not command_after_wake:

                    self.speak("Yes?")
                    continue

                command_text = command_after_wake

            else:

                command_text = heard

            self.process_command(
                command_text
            )

        self.set_gui_status(
            "STOPPED",
            "Voice system stopped."
        )

        self.gui_log(
            "[SYSTEM] Voice engine stopped."
        )

    # ==========================================================
    # COMMAND PROCESSING
    # ==========================================================

    def process_command(self, heard, _bypass_permission=False):

        self.set_gui_status(
            "PROCESSING",
            "Understanding command..."
        )

        # IMPORTANT:
        # Preserve spaces.
        command_text = heard.strip()

        if not command_text:
            return

        # =====================================================
        # PERMISSION & SAFETY
        # =====================================================

        # Resolve a pending confirmation before normal command routing.
        if self.permissions.has_pending():

            result, original_command = (
                self.permissions.handle_response(
                    command_text
                )
            )

            if result == "confirmed":

                self.gui_log(
                    "[SAFETY] Action confirmed."
                )

                # Execute the original command once, bypassing
                # the confirmation gate so it cannot loop.
                return self.process_command(
                    original_command,
                    _bypass_permission=True
                )

            if result == "cancelled":

                self.gui_log(
                    "[SAFETY] Action cancelled."
                )

                self.speak(
                    "Cancelled."
                )

                return

            self.speak(
                "Please say yes to confirm or no to cancel."
            )

            return

        if (
            not _bypass_permission
            and self.permissions.requires_confirmation(
                command_text
            )
        ):

            self.gui_log(
                "[SAFETY] Confirmation required."
            )

            self.speak(
                self.permissions.request_confirmation(
                    command_text
                )
            )

            return

        # =====================================================
        # SKILL SYSTEM
        # =====================================================

        skill_response = self._try_skill(
            command_text
        )

        if skill_response is not None:

            self.context.set_context(
                command=command_text,
                action="skill"
            )

            self.speak(
                skill_response
            )

            return

        # =====================================================
        # CONTEXT
        # =====================================================

        context_response = (
            self._handle_context_command(
                command_text
            )
        )

        if context_response is not None:

            self.speak(
                context_response
            )

            return

        # =====================================================
        # CLOSE WINDOW
        # =====================================================

        close_response = (
            self._handle_direct_close(
                command_text
            )
        )

        if close_response is not None:

            self.speak(
                close_response
            )

            self.context.set_context(
                command=command_text,
                action="window_close"
            )

            return

        # =====================================================
        # MULTI STEP
        # =====================================================

        if self._is_multi_step_command(
            command_text
        ):

            self.set_gui_status(
                "THINKING",
                "Planning multiple actions..."
            )

            self.gui_log(
                "[AGENT] Multi-step command detected."
            )

            agent_response = (
                self.agent.execute(
                    command_text
                )
            )

            if agent_response:

                self._update_context_from_command(
                    command_text
                )

                self.speak(
                    agent_response
                )

                return

        # =====================================================
        # INTENT PARSER
        # =====================================================

        intent = self.intent.parse(
            command_text
        )

        if intent:

            response = self.handle_intent(
                intent
            )

            if response:
                self.speak(response)

            self._update_context_from_intent(
                command_text,
                intent
            )

            return

        # =====================================================
        # NORMAL COMMAND PARSER
        # =====================================================

        command = parse(
            command_text
        )

        if command and command.action == "exit":

            self.speak(
                "Goodbye."
            )

            self.running = False
            self.awake = False

            return

        if command:

            if command.action == "open":

                target = command.target

                success = open_item(
                    target
                )

                if success:

                    response = (
                        f"Opening {target}."
                    )

                else:

                    response = (
                        f"I couldn't find {target}."
                    )

                self.context.set_context(
                    app=target,
                    command=command_text,
                    action="open",
                    target=target
                )

                self.speak(
                    response
                )

                return

        # =====================================================
        # AGENT
        # =====================================================

        self.set_gui_status(
            "THINKING",
            "Planning..."
        )

        agent_response = (
            self.agent.execute(
                command_text
            )
        )

        if agent_response:

            self._update_context_from_command(
                command_text
            )

            self.speak(
                agent_response
            )

            return

        # =====================================================
        # LOCAL AI
        # =====================================================

        self.set_gui_status(
            "THINKING",
            "Asking my local AI..."
        )

        response = self.ai.ask(
            command_text
        )

        self.context.set_context(
            command=command_text,
            action="conversation"
        )

        self.speak(
            response
        )

    # ==========================================================
    # SKILL SYSTEM
    # ==========================================================

    def _try_skill(self, command_text):

        try:

            skill = self.skills.find_skill(
                command_text
            )

            if not skill:
                return None

            self.gui_log(
                f"[SKILL] {skill.name}"
            )

            self.set_gui_status(
                "THINKING",
                f"Using {skill.name} skill..."
            )

            response = skill.execute(
                command_text
            )

            return response

        except Exception as error:

            print(
                f"Skill system error: {error}"
            )

            return None

    # ==========================================================
    # CONTEXT COMMANDS
    # ==========================================================

    def _handle_context_command(
        self,
        command_text
    ):

        text = command_text.lower().strip()

        context = self.context.get_context()

        current_app = context.get("app")
        current_website = context.get("website")
        current_media = context.get("media")

        youtube_active = (
            current_media == "youtube"
            or current_website == "youtube"
            or current_app == "youtube"
        )

        # PLAY

        if text in (
            "play",
            "play it",
            "play that",
            "play the video",
            "resume",
            "resume it",
        ):

            if youtube_active:

                response = (
                    self.media.play_pause()
                )

                self.context.set_context(
                    app="youtube",
                    website="youtube",
                    media="youtube",
                    action="play",
                    command=command_text
                )

                return response

        # PAUSE

        if text in (
            "pause",
            "pause it",
            "pause that",
            "pause the video",
        ):

            if youtube_active:

                response = (
                    self.media.play_pause()
                )

                self.context.set_context(
                    app="youtube",
                    website="youtube",
                    media="youtube",
                    action="pause",
                    command=command_text
                )

                return response

        # MUTE

        if text in (
            "mute it",
            "mute that",
            "mute the video",
            "mute",
        ):

            if youtube_active:

                response = (
                    self.media.mute()
                )

                self.context.set_context(
                    app="youtube",
                    website="youtube",
                    media="youtube",
                    action="mute",
                    command=command_text
                )

                return response

        # FULLSCREEN

        if text in (
            "fullscreen",
            "full screen",
            "make it fullscreen",
            "make it full screen",
            "put it fullscreen",
            "put it in fullscreen",
        ):

            if youtube_active:

                response = (
                    self.media.fullscreen()
                )

                self.context.set_context(
                    app="youtube",
                    website="youtube",
                    media="youtube",
                    action="fullscreen",
                    command=command_text
                )

                return response

        # NEXT

        if text in (
            "next",
            "next video",
            "play next",
            "next one",
        ):

            if youtube_active:

                response = (
                    self.media.next_video()
                )

                self.context.set_context(
                    app="youtube",
                    website="youtube",
                    media="youtube",
                    action="next",
                    command=command_text
                )

                return response

        # FORWARD

        if text in (
            "forward",
            "forward it",
            "skip forward",
            "go forward",
        ):

            if youtube_active:

                response = (
                    self.media.seek_forward()
                )

                self.context.set_context(
                    app="youtube",
                    website="youtube",
                    media="youtube",
                    action="forward",
                    command=command_text
                )

                return response

        # BACK

        if text in (
            "back",
            "backward",
            "go back",
            "skip back",
            "go backward",
        ):

            if youtube_active:

                response = (
                    self.media.seek_backward()
                )

                self.context.set_context(
                    app="youtube",
                    website="youtube",
                    media="youtube",
                    action="backward",
                    command=command_text
                )

                return response

        # CLEAR CONTEXT

        if text in (
            "clear context",
            "forget current context",
            "reset context",
            "start fresh",
        ):

            self.context.clear()

            return (
                "Current conversation context cleared."
            )

        # CONTEXT STATUS

        if text in (
            "what are we doing",
            "what am i doing",
            "what are you controlling",
            "what is the current context",
        ):

            if not current_app and not current_website:

                return (
                    "There is no active context."
                )

            target = (
                current_media
                or current_website
                or current_app
            )

            return (
                f"We are currently working "
                f"with {target}."
            )

        return None

    # ==========================================================
    # CONTEXT FROM INTENT
    # ==========================================================

    def _update_context_from_intent(
        self,
        command_text,
        intent
    ):

        action = intent.action
        target = intent.target

        youtube_actions = (
            "youtube_play_pause",
            "youtube_mute",
            "youtube_fullscreen",
            "youtube_next",
            "youtube_forward",
            "youtube_backward",
            "youtube_search",
        )

        if action in youtube_actions:

            self.context.set_context(
                app="youtube",
                website="youtube",
                media="youtube",
                command=command_text,
                action=action,
                target=target
            )

            return

        if action == "google_search":

            self.context.set_context(
                app="google",
                website="google",
                command=command_text,
                action=action,
                target=target
            )

            return

        if action == "open_website":

            website = target

            self.context.set_context(
                app=website,
                website=website,
                command=command_text,
                action=action,
                target=target
            )

            return

        self.context.set_context(
            command=command_text,
            action=action,
            target=target
        )

    # ==========================================================
    # CONTEXT FROM AGENT
    # ==========================================================

    def _update_context_from_command(
        self,
        command_text
    ):

        text = command_text.lower().strip()

        if (
            "youtube" in text
            or "video" in text
        ):

            self.context.set_context(
                app="youtube",
                website="youtube",
                media="youtube",
                command=command_text
            )

            search_match = re.search(
                r"(?:search|find|look for)"
                r"(?: for)? (.+?)"
                r"(?: on youtube)?$",
                text
            )

            if search_match:

                query = (
                    search_match.group(
                        1
                    ).strip()
                )

                self.context.set_context(
                    target=query
                )

            return

        if "google" in text:

            self.context.set_context(
                app="google",
                website="google",
                command=command_text
            )

            return

        self.context.set_context(
            command=command_text
        )

    # ==========================================================
    # MULTI STEP
    # ==========================================================

    def _is_multi_step_command(
        self,
        command_text
    ):

        text = command_text.lower().strip()

        markers = (
            " and ",
            " then ",
            " after that ",
            ", and ",
            ", then ",
        )

        if any(
            marker in text
            for marker in markers
        ):

            return True

        multi_action_patterns = (
            r"\bopen .+ search\b",
            r"\bopen .+ find\b",
            r"\bcheck .+ battery\b",
            r"\bcheck .+ ram\b",
            r"\bcheck .+ cpu\b",
            r"\bsearch .+ fullscreen\b",
        )

        for pattern in multi_action_patterns:

            if re.search(
                pattern,
                text
            ):

                return True

        return False

    # ==========================================================
    # CLOSE
    # ==========================================================

    def _handle_direct_close(
        self,
        command_text
    ):

        text = command_text.lower().strip()

        current_patterns = (
            r"^close$",
            r"^close window$",
            r"^close this window$",
            r"^close current window$",
            r"^close the current window$",
            r"^close active window$",
            r"^close the active window$",
            r"^close this$",
        )

        for pattern in current_patterns:

            if re.fullmatch(
                pattern,
                text
            ):

                return (
                    self.windows.close_current()
                )

        patterns = (
            r"^close (.+)$",
            r"^close the (.+)$",
            r"^shut (.+)$",
            r"^shut the (.+)$",
        )

        for pattern in patterns:

            match = re.fullmatch(
                pattern,
                text
            )

            if not match:
                continue

            target = (
                match.group(1).strip()
            )

            if not target:
                return None

            if target in (
                "window",
                "this window",
                "current window",
                "the current window",
                "active window",
                "the active window",
            ):

                return (
                    self.windows.close_current()
                )

            return (
                self.windows.close(target)
            )

        return None

    # ==========================================================
    # SPEAK
    # ==========================================================

    def speak(self, text):

        if not text:
            return

        self.gui_log(
            f"FRIDAY: {text}"
        )

        self.set_gui_status(
            "SPEAKING",
            "FRIDAY is responding..."
        )

        self.speaker.speak(
            text
        )

        self._wait_for_speech()

        if self.running:

            self.set_gui_status(
                "LISTENING",
                "Listening for your command..."
            )

    def _wait_for_speech(self):

        while (
            self.speaker.speaking
            and self.running
        ):

            time.sleep(0.05)

    # ==========================================================
    # INTENT HANDLER
    # ==========================================================

    def handle_intent(self, intent):

        action = intent.action
        target = intent.target

        # MEMORY

        if action == "remember":
            return self.memory.remember(target)

        if action == "forget":
            return self.memory.forget(target)

        if action == "memory":

            memories = self.memory.get_all()

            if not memories:

                return (
                    "I don't have anything saved "
                    "in memory."
                )

            return (
                "I remember: "
                + ". ".join(
                    memories[:10]
                )
            )

        # DEVELOPER

        if action == "developer_terminal":
            return self.developer.open_terminal()

        if action == "developer_powershell":
            return self.developer.open_powershell()

        if action == "developer_project":
            return self.developer.open_project_folder()

        if action == "developer_files":
            return self.developer.show_project_files()

        # WINDOWS

        if action == "window_close":
            return self.windows.close(target)

        if action == "window_close_current":
            return self.windows.close_current()

        # CLIPBOARD

        if action == "clipboard_read":

            text = self.clipboard.get_text()

            if text is None:
                return "The clipboard is empty."

            if not text.strip():
                return "The clipboard contains no text."

            preview = text.strip()

            if len(preview) > 300:
                preview = preview[:300] + "..."

            return (
                "The clipboard contains: "
                + preview
            )

        if action == "clipboard_clear":

            if self.clipboard.clear():
                return "Clipboard cleared."

            return (
                "I couldn't clear the clipboard."
            )

        if action == "clipboard_copy":
            return self._copy_to_clipboard()

        if action == "clipboard_paste":
            return self._paste_clipboard()

        # KEYBOARD

        if action == "key_enter":
            return self.input.enter()

        if action == "key_escape":
            return self.input.escape()

        if action == "key_tab":
            return self.input.tab()

        if action == "key_backspace":
            return self.input.backspace()

        if action == "key_space":
            return self.input.space()

        if action == "key_windows":
            return self.input.windows_key()

        if action == "key_ctrl_c":
            return self.input.ctrl_c()

        if action == "key_ctrl_v":
            return self.input.ctrl_v()

        if action == "key_ctrl_x":
            return self.input.ctrl_x()

        if action == "key_ctrl_a":
            return self.input.ctrl_a()

        if action == "key_alt_tab":
            return self.input.alt_tab()

        # TEXT

        if action == "type_text":

            if not target:
                return "What should I type?"

            return (
                self.input.type_text(target)
            )

        # MOUSE

        if action == "mouse_click":
            return self.input.click()

        if action == "mouse_right_click":
            return self.input.right_click()

        if action == "mouse_double_click":
            return self.input.double_click()

        # YOUTUBE

        if action == "youtube_play_pause":

            response = (
                self.media.play_pause()
            )

            self.context.set_context(
                app="youtube",
                website="youtube",
                media="youtube",
                action=action,
                command=target
            )

            return response

        if action == "youtube_mute":

            response = (
                self.media.mute()
            )

            self.context.set_context(
                app="youtube",
                website="youtube",
                media="youtube",
                action=action
            )

            return response

        if action == "youtube_fullscreen":

            response = (
                self.media.fullscreen()
            )

            self.context.set_context(
                app="youtube",
                website="youtube",
                media="youtube",
                action=action
            )

            return response

        if action == "youtube_next":

            response = (
                self.media.next_video()
            )

            self.context.set_context(
                app="youtube",
                website="youtube",
                media="youtube",
                action=action
            )

            return response

        if action == "youtube_forward":

            response = (
                self.media.seek_forward()
            )

            self.context.set_context(
                app="youtube",
                website="youtube",
                media="youtube",
                action=action
            )

            return response

        if action == "youtube_backward":

            response = (
                self.media.seek_backward()
            )

            self.context.set_context(
                app="youtube",
                website="youtube",
                media="youtube",
                action=action
            )

            return response

        # WEBSITE

        if action == "open_website":

            response = self.web.open_website(
                target,
                browser=getattr(
                    intent,
                    "browser",
                    None
                )
            )

            self.context.set_context(
                app=target,
                website=target,
                command=target,
                action=action,
                target=target
            )

            return response

        if action == "open_website_brave":

            response = self.web.open_website(
                target,
                browser="brave"
            )

            self.context.set_context(
                app=target,
                website=target,
                target=target,
                action=action
            )

            return response

        # GOOGLE

        if action == "google_search":

            response = self.web.search_google(
                target,
                browser=getattr(
                    intent,
                    "browser",
                    None
                )
            )

            self.context.set_context(
                app="google",
                website="google",
                target=target,
                action=action
            )

            return response

        if action == "google_search_brave":

            response = self.web.search_google(
                target,
                browser="brave"
            )

            self.context.set_context(
                app="google",
                website="google",
                target=target,
                action=action
            )

            return response

        # YOUTUBE SEARCH

        if action == "youtube_search":

            response = self.web.search_youtube(
                target,
                browser=getattr(
                    intent,
                    "browser",
                    None
                )
            )

            self.context.set_context(
                app="youtube",
                website="youtube",
                media="youtube",
                target=target,
                action=action
            )

            return response

        if action == "youtube_search_brave":

            response = self.web.search_youtube(
                target,
                browser="brave"
            )

            self.context.set_context(
                app="youtube",
                website="youtube",
                media="youtube",
                target=target,
                action=action
            )

            return response

        # SYSTEM

        if action == "cpu":
            return self.monitor.cpu_usage()

        if action == "ram":
            return self.monitor.ram_usage()

        if action == "disk":
            return self.monitor.disk_usage()

        if action == "battery":
            return self.monitor.battery()

        if action == "uptime":
            return self.monitor.uptime()

        if action == "network":
            return self.monitor.network()

        # VOLUME

        if action == "volume_up":
            return self.system.volume_up()

        if action == "volume_down":
            return self.system.volume_down()

        if action == "mute":
            return self.system.mute()

        if action == "unmute":
            return self.system.unmute()

        # POWER

        if action == "lock":
            return self.system.lock()

        if action == "sleep":
            return self.system.sleep()

        if action == "restart":
            return self.system.restart()

        if action == "shutdown":
            return self.system.shutdown()

        if action == "cancel_shutdown":
            return self.system.cancel_shutdown()

        return None

    # ==========================================================
    # CLIPBOARD HELPERS
    # ==========================================================

    def _copy_to_clipboard(self):

        self.input.ctrl_c()

        time.sleep(0.2)

        text = (
            self.clipboard.get_text()
        )

        if text is None:
            return (
                "I couldn't read the copied text."
            )

        if not text.strip():
            return "Nothing was copied."

        return (
            "Copied the selected text."
        )

    def _paste_clipboard(self):

        text = (
            self.clipboard.get_text()
        )

        if text is None:
            return "The clipboard is empty."

        self.input.ctrl_v()

        return (
            "Pasted the clipboard contents."
        )