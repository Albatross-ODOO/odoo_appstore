/** @odoo-module **/

import { Component, onWillStart, onWillUnmount, markup, proxy, signal, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

const MESSAGE_PAGE = 300;
// participant tags shown in the conversation header; the others are summed up in a "+N more" tag
const MAX_HEADER_PARTNERS = 8;

export class ChatMonitorView extends Component {
    static template = "discuss_chat_monitor.ChatMonitorView";
    props = useProps(standardActionServiceProps);

    setup() {
        this.orm = useService("orm");
        this.threadRef = signal.ref();

        this.state = proxy({
            sessions: [],
            selectedSession: null,
            messages: [],
            searchTerm: "",
            activeFilter: "all",
            dateFilter: "all",
            isLoadingSessions: true,
            isLoadingMessages: false,
            messageLimit: MESSAGE_PAGE,
            hasOlderMessages: false,
            // the menu is hidden without the group, but the action can still be opened by its URL
            hasAccess: true,
        });

        // responses of superseded requests (typing, fast clicks) must not overwrite newer ones
        this.sessionsRequest = 0;
        this.messagesRequest = 0;
        onWillStart(async () => {
            this.state.hasAccess = await user.hasGroup("discuss_chat_monitor.group_chat_monitor_admin");
            if (this.state.hasAccess) {
                await this.loadSessions();
            }
        });
        onWillUnmount(() => clearTimeout(this.searchTimer));
    }

    get headerPartners() {
        return (this.state.selectedSession?.partners || []).slice(0, MAX_HEADER_PARTNERS);
    }

    get hiddenPartners() {
        return (this.state.selectedSession?.partners || []).slice(MAX_HEADER_PARTNERS);
    }

    get hiddenPartnersTitle() {
        return this.hiddenPartners.map((p) => p.name).join(", ");
    }

    get allPartnersTitle() {
        return (this.state.selectedSession?.partners || []).map((p) => p.name).join(", ");
    }

    async loadSessions() {
        const request = ++this.sessionsRequest;
        this.state.isLoadingSessions = true;
        try {
            const sessions = await this.orm.call("discuss.channel", "get_monitor_channels", [], {
                search_term: this.state.searchTerm,
                filter_type: this.state.activeFilter,
                date_filter: this.state.dateFilter,
            });
            if (request !== this.sessionsRequest) {
                return;
            }
            this.state.sessions = sessions;

            if (this.state.selectedSession) {
                const updated = sessions.find((s) => s.id === this.state.selectedSession.id);
                if (updated) {
                    this.state.selectedSession = updated;
                    await this.selectSession(updated);
                } else {
                    this.state.selectedSession = sessions.length > 0 ? sessions[0] : null;
                    if (this.state.selectedSession) {
                        await this.selectSession(this.state.selectedSession);
                    }
                }
            } else if (sessions.length > 0) {
                await this.selectSession(sessions[0]);
            }
        } catch (error) {
            console.error("Error loading chat sessions:", error);
        } finally {
            if (request === this.sessionsRequest) {
                this.state.isLoadingSessions = false;
            }
        }
    }

    async selectSession(session, { loadOlder = false } = {}) {
        const request = ++this.messagesRequest;
        if (!loadOlder && this.state.selectedSession?.id !== session.id) {
            this.state.messageLimit = MESSAGE_PAGE;
        }
        this.state.selectedSession = session;
        this.state.isLoadingMessages = true;
        try {
            const data = await this.orm.call("discuss.channel", "get_channel_messages", [session.id], {
                date_filter: this.state.dateFilter,
                limit: this.state.messageLimit,
            });
            if (request !== this.messagesRequest) {
                return;
            }
            const messages = (data.messages || []).map((msg) => ({
                ...msg,
                body: markup(msg.body || ""),
            }));
            this.state.messages = messages;
            this.state.hasOlderMessages = Boolean(data.channel && data.channel.message_count > messages.length);
            if (data.channel) {
                this.state.selectedSession = { ...session, ...data.channel };
            }
            if (!loadOlder) {
                this.scrollToBottom();
            }
        } catch (error) {
            console.error("Error loading channel messages:", error);
        } finally {
            if (request === this.messagesRequest) {
                this.state.isLoadingMessages = false;
            }
        }
    }

    async onFilterChange(filter) {
        this.state.activeFilter = filter;
        await this.loadSessions();
    }

    async onDateFilterChange(dateFilter) {
        this.state.dateFilter = dateFilter;
        await this.loadSessions();
    }

    onSearchInput(ev) {
        this.state.searchTerm = ev.target.value;
        clearTimeout(this.searchTimer);
        this.searchTimer = setTimeout(() => this.loadSessions(), 300);
    }

    async loadOlderMessages() {
        this.state.messageLimit += MESSAGE_PAGE;
        await this.selectSession(this.state.selectedSession, { loadOlder: true });
    }

    async refreshCurrentSession() {
        if (this.state.selectedSession) {
            await this.selectSession(this.state.selectedSession);
        }
    }

    scrollToBottom() {
        setTimeout(() => {
            const thread = this.threadRef();
            if (thread) {
                thread.scrollTop = thread.scrollHeight;
            }
        }, 100);
    }
}

registry.category("actions").add("discuss_chat_monitor.chat_monitor_dashboard", ChatMonitorView);
