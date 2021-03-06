from dataclasses import asdict
from typing import Union, Optional, List

from aqt import mw

from anki.cards import Card
from anki.models import NoteType

from .config_types import (
    ScriptSetting,
    Script,
    ConcreteScript,
    MetaScript,
    ScriptStorage,
    DEFAULT_SETTING,
    DEFAULT_CONCRETE_SCRIPT,
    DEFAULT_META_SCRIPT,
    HTMLSetting,
    HTML,
    ConcreteHTML,
    DEFAULT_HTML_SETTING,
    DEFAULT_CONCRETE_HTML,
)

from .lib.interface import (
    make_setting,
    make_script_v2,
    make_meta_script,
    make_script_storage,
    make_html_setting,
    make_fragment,
)

from .lib.registrar import (
    get_interface,
    get_meta_scripts,
)

from .utils import (
    scripts_config,
    html_config,
)

######################## SCRIPTS


def deserialize_setting(model_id: int, model_setting: dict) -> ScriptSetting:
    return make_setting(
        model_setting["enabled"]
        if "enabled" in model_setting
        else DEFAULT_SETTING.enabled,
        model_setting["insertStub"]
        if "insertStub" in model_setting
        else DEFAULT_SETTING.insert_stub,
        model_setting["indentSize"]
        if "indentSize" in model_setting
        else DEFAULT_SETTING.indent_size,
        add_other_metas(
            model_id,
            [
                s
                for s in [
                    deserialize_script(script)
                    for script in (
                        model_setting["scripts"]
                        if "scripts" in model_setting
                        else DEFAULT_SETTING.scripts
                    )
                ]
                if s
            ],
        ),
    )


def should_autodelete(script: Script) -> bool:
    if isinstance(script, ConcreteScript):
        return False

    interface = get_interface(script.tag)

    if isinstance(interface.autodelete, bool):
        return interface.autodelete

    return interface.autodelete(script.id, script.storage)


def add_other_metas(model_id: int, scripts: List[Script]) -> List[Script]:
    meta_scripts = get_meta_scripts(model_id)

    for ms in meta_scripts:
        try:
            found = next(
                filter(
                    lambda script: isinstance(script, MetaScript)
                    and script.tag == ms.tag
                    and script.id == ms.id,
                    scripts,
                )
            )
        except StopIteration:
            # newly inserted meta scripts, which were not written to config before
            scripts.append(
                make_meta_script(
                    ms.tag,
                    ms.id,
                )
            )

    return list(filter(lambda script: not should_autodelete(script), scripts))


def deserialize_script(script_data: dict) -> Union[ConcreteScript, MetaScript]:
    return (
        script_data
        if isinstance(script_data, Script)
        else (
            deserialize_concrete_script(script_data)
            if "name" in script_data
            else deserialize_meta_script(script_data)
        )
    )


def deserialize_concrete_script(script_data: dict) -> ConcreteScript:
    return make_script_v2(
        name=script_data["name"]
        if "name" in script_data
        else DEFAULT_CONCRETE_SCRIPT.name,
        enabled=script_data["enabled"]
        if "enabled" in script_data
        else DEFAULT_CONCRETE_SCRIPT.enabled,
        type=script_data["type"]
        if "type" in script_data
        else DEFAULT_CONCRETE_SCRIPT.type,
        label=script_data["label"]
        if "label" in script_data
        else DEFAULT_CONCRETE_SCRIPT.label,
        version=script_data["version"]
        if "version" in script_data
        else DEFAULT_CONCRETE_SCRIPT.version,
        description=script_data["description"]
        if "description" in script_data
        else DEFAULT_CONCRETE_SCRIPT.description,
        position=script_data["position"]
        if "position" in script_data
        else DEFAULT_CONCRETE_SCRIPT.position,
        conditions=script_data["conditions"]
        if "conditions" in script_data
        else DEFAULT_CONCRETE_SCRIPT.conditions,
        code=script_data["code"]
        if "code" in script_data
        else DEFAULT_CONCRETE_SCRIPT.code,
    )


def deserialize_meta_script(script_data: dict) -> MetaScript:
    result = make_meta_script(
        script_data["tag"] if "tag" in script_data else DEFAULT_META_SCRIPT.tag,
        script_data["id"] if "id" in script_data else DEFAULT_META_SCRIPT.id,
        make_script_storage(
            **script_data["storage"]
            if "storage" in script_data
            else DEFAULT_META_SCRIPT.storage
        ),
    )

    return result


def serialize_setting(setting: ScriptSetting) -> dict:
    return {
        "enabled": setting.enabled,
        "insertStub": setting.insert_stub,
        "indentSize": setting.indent_size,
        "scripts": [serialize_script(script) for script in setting.scripts],
    }


def serialize_script(script: Union[ConcreteScript, MetaScript]) -> dict:
    if isinstance(script, ConcreteScript):
        return asdict(script)
    else:
        preresult = asdict(script)

        return {
            "tag": preresult["tag"],
            "id": preresult["id"],
            "storage": {k: v for k, v in preresult["storage"].items() if v is not None},
        }


def get_setting_from_notetype(notetype) -> ScriptSetting:
    scripts_config.model_id = notetype["id"]

    return deserialize_setting(
        scripts_config.model_id,
        scripts_config.value,
    )


def maybe_get_setting_from_card(card) -> Optional[ScriptSetting]:
    the_note = Card(mw.col, card.id).note()
    maybe_model = the_note.model()

    return get_setting_from_notetype(maybe_model) if maybe_model else None


######################## HTML


def deserialize_html_setting(_model_id: int, model_setting: dict) -> ScriptSetting:
    return make_html_setting(
        model_setting["enabled"]
        if "enabled" in model_setting
        else DEFAULT_HTML_SETTING.enabled,
        model_setting["minify"]
        if "minify" in model_setting
        else DEFAULT_HTML_SETTING.minify,
        [
            deserialize_html(fragment)
            for fragment in (
                model_setting["fragments"]
                if "fragments" in model_setting
                else DEFAULT_HTML_SETTING.fragments
            )
        ],
    )


def deserialize_html(script_data: dict) -> ConcreteHTML:
    return (
        script_data
        if isinstance(script_data, HTML)
        else make_fragment(
            script_data["name"]
            if "name" in script_data
            else DEFAULT_CONCRETE_HTML.name,
            script_data["enabled"]
            if "enabled" in script_data
            else DEFAULT_CONCRETE_HTML.enabled,
            script_data["label"]
            if "label" in script_data
            else DEFAULT_CONCRETE_HTML.label,
            script_data["version"]
            if "version" in script_data
            else DEFAULT_CONCRETE_HTML.version,
            script_data["description"]
            if "description" in script_data
            else DEFAULT_CONCRETE_HTML.description,
            script_data["conditions"]
            if "conditions" in script_data
            else DEFAULT_CONCRETE_HTML.conditions,
            script_data["code"]
            if "code" in script_data
            else DEFAULT_CONCRETE_HTML.code,
        )
    )


def serialize_html_setting(setting: HTMLSetting) -> dict:
    return {
        "enabled": setting.enabled,
        "minify": setting.minify,
        "fragments": [serialize_html(script) for script in setting.fragments],
    }


def serialize_html(fragment: Union[ConcreteHTML]) -> dict:
    return asdict(fragment)


def get_html_setting_from_notetype(notetype: NoteType) -> HTMLSetting:
    html_config.model_id = notetype["id"]

    return deserialize_html_setting(
        html_config.model_id,
        html_config.value,
    )


######################## together


def write_html(
    html: HTMLSetting, /, model_id: int = None, custom_model: NoteType = None
):
    if custom_model:
        html_config.model = custom_model
    elif model_id:
        html_config.model_id = model_id

    html_config.value = serialize_html_setting(html)


def write_scripts(
    scripts: ScriptSetting, /, model_id: int = None, custom_model: NoteType = None
):
    if custom_model:
        scripts_config.model = custom_model
    elif model_id:
        scripts_config.model_id = model_id

    scripts_config.value = serialize_setting(scripts)


def write_setting(
    html: HTMLSetting,
    scripts: ScriptSetting,
    /,
    model_id: int = None,
    custom_model: NoteType = None,
):
    write_html(html, model_id=model_id, custom_model=custom_model)
    write_scripts(scripts, model_id=model_id, custom_model=custom_model)
