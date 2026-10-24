// Point of Sale (/pos/ui) is its own app, outside the web client: the server template does not put the
// look's classes on its page. They come with the session (models/ir_http.py session_info) and go on <html>
// when this module loads, so a look's POS stylesheet can scope itself (`html.o_aic_skin_<look> .pos`).
import { session } from "@web/session";

if (session.aic_skin) {
    document.documentElement.classList.add("o_aic_theme", "o_aic_skin_" + session.aic_skin);
}
