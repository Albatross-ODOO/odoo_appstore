/** @odoo-module **/

import { Component, useState, onWillStart, useRef, markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ChatMonitorView extends Component {
    static template = "discuss_chat_monitor.ChatMonitorView";

    setup() {
        this.orm = useService("orm");
        this.threadRef = useRef("chatThread");

        this.state = useState({
            sessions: [],
            selectedSession: null,
            messages: [],
            searchTerm: "",
            activeFilter: "all",
            dateFilter: "all",
            isLoadingSessions: true,
            isLoadingMessages: false,
        });

        onWillStart(async () => {
            await this.loadSessions();
        });
    }

    async loadSessions() {
        this.state.isLoadingSessions = true;
        try {
            const sessions = await this.orm.call("discuss.channel", "get_monitor_channels", [], {
                search_term: this.state.searchTerm,
                filter_type: this.state.activeFilter,
                date_filter: this.state.dateFilter,
            });
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
            this.state.isLoadingSessions = false;
        }
    }

    async selectSession(session) {
        this.state.selectedSession = session;
        this.state.isLoadingMessages = true;
        try {
            const data = await this.orm.call("discuss.channel", "get_channel_messages", [session.id], {
                date_filter: this.state.dateFilter,
            });
            const messages = (data.messages || []).map((msg) => ({
                ...msg,
                body: markup(msg.body || ""),
            }));
            this.state.messages = messages;
            if (data.channel) {
                this.state.selectedSession = { ...session, ...data.channel };
            }
            this.scrollToBottom();
        } catch (error) {
            console.error("Error loading channel messages:", error);
        } finally {
            this.state.isLoadingMessages = false;
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

    async onSearchInput(ev) {
        this.state.searchTerm = ev.target.value;
        await this.loadSessions();
    }

    async refreshCurrentSession() {
        if (this.state.selectedSession) {
            await this.selectSession(this.state.selectedSession);
        }
    }

    scrollToBottom() {
        setTimeout(() => {
            if (this.threadRef.el) {
                this.threadRef.el.scrollTop = this.threadRef.el.scrollHeight;
            }
        }, 100);
    }
}

registry.category("actions").add("discuss_chat_monitor.chat_monitor_dashboard", ChatMonitorView);
