// On-demand app search plus time-bounded arithmetic, using Rofi's plugin ABI.
#include <rofi/mode-private.h>
#include <libqalculate/Calculator.h>
#include <libqalculate/MathStructure.h>
#include <cctype>
#include <cstdio>
#include <memory>
#include <string>

extern "C" Mode *rofi_collect_modes_search(const char *name);

struct SmartData {
    Mode *apps = nullptr;
    std::unique_ptr<Calculator> calculator;
    std::string previous;
    std::string result;
};

static bool math_query(std::string &input) {
    const auto first = input.find_first_not_of(" \t");
    if (first == std::string::npos) return false;
    input.erase(0, first);
    if (input[0] == '=') { input.erase(0, 1); return !input.empty(); }
    if (std::isdigit(static_cast<unsigned char>(input[0])) || input[0] == '(' || input[0] == '.' || input[0] == '+' || input[0] == '-') return true;
    for (const char *function : {"sqrt(", "sin(", "cos(", "tan(", "log(", "ln(", "abs(", "round("})
        if (input.starts_with(function)) return true;
    return false;
}

static int smart_init(Mode *sw) {
    if (sw->private_data) return TRUE;
    auto data = std::make_unique<SmartData>();
    data->apps = rofi_collect_modes_search("drun");
    if (!data->apps || !mode_init(data->apps)) return FALSE;
    sw->private_data = data.release();
    return TRUE;
}

static void smart_destroy(Mode *sw) {
    auto *data = static_cast<SmartData *>(sw->private_data);
    if (data) {
        mode_destroy(data->apps);
        delete data;
        sw->private_data = nullptr;
    }
}

static unsigned int smart_count(const Mode *sw) {
    return mode_get_num_entries(static_cast<SmartData *>(sw->private_data)->apps)+1;
}

static char *smart_preprocess(Mode *sw, const char *input) {
    auto *data = static_cast<SmartData *>(sw->private_data);
    const std::string query = input ? input : "";
    if (query != data->previous) {
        data->previous = query;
        data->result.clear();
        std::string expression = query;
        if (math_query(expression)) {
            if (!data->calculator) {
                data->calculator = std::make_unique<Calculator>(true);
                data->calculator->loadGlobalDefinitions();
            }
            data->calculator->beginTemporaryStopMessages();
            MathStructure result;
            const bool finished = data->calculator->calculate(&result, expression, 250);
            int messages = 0, warnings = 0;
            data->calculator->endTemporaryStopMessages(&messages, &warnings);
            if (finished && !result.isUndefined() && !result.isAborted() && messages == 0 && warnings == 0) {
                data->result = data->calculator->print(result, 100);
                if (data->calculator->aborted() || data->result.size()>512) data->result.clear();
            }
            data->calculator->clearMessages();
        }
    }
    return g_strdup(input ? input : "");
}

static int smart_match(const Mode *sw, rofi_int_matcher **tokens, unsigned int index) {
    auto *data = static_cast<SmartData *>(sw->private_data);
    return index == 0 ? !data->result.empty() : mode_token_match(data->apps, tokens, index-1);
}

static char *smart_display(const Mode *sw, unsigned int index, int *state, GList **attrs, int get_entry) {
    auto *data = static_cast<SmartData *>(sw->private_data);
    if (index == 0) return get_entry ? g_strdup_printf("= %s", data->result.c_str()) : nullptr;
    return mode_get_display_value(data->apps, index-1, state, attrs, get_entry);
}

static cairo_surface_t *smart_icon(const Mode *sw, unsigned int index, unsigned int height) {
    auto *data = static_cast<SmartData *>(sw->private_data);
    return index == 0 ? nullptr : mode_get_icon(data->apps, index-1, height);
}

static char *smart_completion(const Mode *sw, unsigned int index) {
    auto *data = static_cast<SmartData *>(sw->private_data);
    return index == 0 ? g_strdup(data->result.c_str()) : mode_get_completion(data->apps, index-1);
}

static char *smart_message(const Mode *sw) {
    auto *data = static_cast<SmartData *>(sw->private_data);
    return data->result.empty() ? mode_get_message(data->apps) : g_strdup("Enter to copy calculation result");
}

static ModeMode smart_result(Mode *sw, int flags, char **input, unsigned int index) {
    auto *data = static_cast<SmartData *>(sw->private_data);
    if (flags & MENU_NEXT) return NEXT_DIALOG;
    if (flags & MENU_PREVIOUS) return PREVIOUS_DIALOG;
    if (flags & MENU_QUICK_SWITCH) return static_cast<ModeMode>(flags & MENU_LOWER_MASK);
    if (flags & MENU_CANCEL) return MODE_EXIT;
    if (index == 0 && !data->result.empty() && (flags & (MENU_OK | MENU_CUSTOM_INPUT))) {
        std::printf("%s\n", data->result.c_str());
        return MODE_EXIT;
    }
    return mode_result(data->apps, flags, input, index > 0 ? index-1 : UINT32_MAX);
}

extern "C" {
Mode mode = {
    .abi_version = ABI_VERSION,
    .name = const_cast<char *>("smart"),
    .cfg_name_key = "display-smart",
    ._init = smart_init,
    ._destroy = smart_destroy,
    ._get_num_entries = smart_count,
    ._result = smart_result,
    ._token_match = smart_match,
    ._get_display_value = smart_display,
    ._get_icon = smart_icon,
    ._get_completion = smart_completion,
    ._preprocess_input = smart_preprocess,
    ._get_message = smart_message,
    .type = MODE_TYPE_SWITCHER,
};
}
