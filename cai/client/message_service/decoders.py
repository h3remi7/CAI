"""MessageSvc message decoder.

This module is used to decode message protobuf.

:Copyright: Copyright (C) 2021-2021  cscs181
:License: AGPL-3.0 or later. See `LICENSE`_ for detail.

.. _LICENSE:
    https://github.com/cscs181/CAI/blob/master/LICENSE
"""

from typing import List, Dict, Optional, Sequence, Callable

from cai.log import logger
from cai.client.event import Event
from cai.pb.msf.msg.comm import Msg
from cai.pb.im.msg.msg_body import Elem
from cai.pb.im.msg.service.comm_elem import (
    MsgElemInfo_servtype2,
    MsgElemInfo_servtype33,
)
from .models import (
    PrivateMessage,
    Element,
    TextElement,
    FaceElement,
    SmallEmojiElement,
    PokeElement,
)


def parse_elements(elems: Sequence[Elem]) -> List[Element]:
    res: List[Element] = []
    index = 0
    while index < len(elems):
        elem = elems[index]
        if elem.HasField("src_msg"):
            ...
        if elem.HasField("text"):
            res.append(TextElement(elem.text.str.decode("utf-8")))
        if elem.HasField("face"):
            res.append(FaceElement(elem.face.index))
        if elem.HasField("small_emoji"):
            index += 1
            text = elems[index].text.str.decode("utf-8")
            res.append(
                SmallEmojiElement(
                    elem.small_emoji.pack_id_sum,
                    text,
                    # bytes(
                    #     [
                    #         0x1FF
                    #         if elem.small_emoji.image_type & 0xFFFF == 2
                    #         else 0xFF,
                    #         elem.small_emoji.pack_id_sum & 0xFFFF,
                    #         elem.small_emoji.pack_id_sum >> 16 & 0xFF,
                    #         elem.small_emoji.pack_id_sum >> 24,
                    #     ]
                    # ),
                )
            )
        if elem.HasField("custom_face"):
            ...
        if elem.HasField("not_online_image"):
            ...
        if elem.HasField("common_elem"):
            service_type = elem.common_elem.service_type
            if service_type == 2:
                poke = MsgElemInfo_servtype2.FromString(
                    elem.common_elem.pb_elem
                )
                res = [
                    PokeElement(
                        poke.poke_type
                        if poke.vaspoke_id == 0xFFFFFFFF
                        else poke.vaspoke_id,
                        poke.vaspoke_name.decode("utf-8"),
                        poke.poke_strength,
                        poke.double_hit,
                    )
                ]
                break
            elif service_type == 33:
                info = MsgElemInfo_servtype33.FromString(
                    elem.common_elem.pb_elem
                )
                res.append(FaceElement(info.index))
            # else:
            #     print(elem)
        # else:
        #     print(elem)
        index += 1
    return res


class BuddyMessageDecoder:
    @classmethod
    def decode(cls, message: Msg) -> Optional[Event]:
        """Buddy Message Decoder.

        Note:
            Source:
            com.tencent.mobileqq.service.message.codec.decoder.buddyMessage.BuddyMessageDecoder
        """
        sub_decoders: Dict[int, Callable[[Msg], Optional[Event]]] = {
            11: cls.decode_normal_buddy,
            # 129: OnlineFileDecoder,
            # 131: OnlineFileDecoder,
            # 133: OnlineFileDecoder,
            # 169: OfflineFileDecoder,
            175: cls.decode_normal_buddy,
            # 241: OfflineFileDecoder,
            # 242: OfflineFileDecoder,
            # 243: OfflineFileDecoder,
        }
        Decoder = sub_decoders.get(message.head.c2c_cmd, None)
        if not Decoder:
            logger.debug(
                "MessageSvc.PbGetMsg: BuddyMessageDecoder cannot "
                f"decode message with c2c_cmd {message.head.c2c_cmd}"
            )
            return
        return Decoder(message)

    @classmethod
    def decode_normal_buddy(cls, message: Msg) -> Optional[Event]:
        """Normal Buddy Message Decoder.

        Note:
            Source:

            com.tencent.mobileqq.service.message.codec.decoder.buddyMessage.NormalBuddyDecoder

            com.tencent.mobileqq.service.message.MessagePBElemDecoder
        """
        if (
            not message.HasField("body")
            or not message.body.HasField("rich_text")
            or not message.body.rich_text.elems
            or not message.HasField("content_head")
        ):
            return

        seq = message.head.seq
        time = message.head.time
        auto_reply = bool(message.content_head.auto_reply)
        from_uin = message.head.from_uin
        from_nick = message.head.from_nick
        to_uin = message.head.to_uin
        elems = message.body.rich_text.elems

        return PrivateMessage(
            seq,
            time,
            auto_reply,
            from_uin,
            from_nick,
            to_uin,
            parse_elements(elems),
        )


MESSAGE_DECODERS: Dict[int, Callable[[Msg], Optional[Event]]] = {
    9: BuddyMessageDecoder.decode,
    10: BuddyMessageDecoder.decode,
    31: BuddyMessageDecoder.decode,
    # 33: TroopAddMemberBroadcastDecoder,
    # 35: TroopSystemMessageDecoder,
    # 36: TroopSystemMessageDecoder,
    # 37: TroopSystemMessageDecoder,
    # 38: CreateGrpInPCDecoder,
    # 45: TroopSystemMessageDecoder,
    # 46: TroopSystemMessageDecoder,
    # 84: TroopSystemMessageDecoder,
    # 85: TroopSystemMessageDecoder,
    # 86: TroopSystemMessageDecoder,
    # 87: TroopSystemMessageDecoder,
    79: BuddyMessageDecoder.decode,
    97: BuddyMessageDecoder.decode,
    120: BuddyMessageDecoder.decode,
    132: BuddyMessageDecoder.decode,
    133: BuddyMessageDecoder.decode,
    # 140: TempSessionDecoder,
    # 141: TempSessionDecoder,
    166: BuddyMessageDecoder.decode,
    167: BuddyMessageDecoder.decode,
    # 187: SystemMessageDecoder,
    # 188: SystemMessageDecoder,
    # 189: SystemMessageDecoder,
    # 190: SystemMessageDecoder,
    # 191: SystemMessageDecoder,
    # 193: VideoDecoder,
    # 208: PTTDecoder,
    # 519: MultiVideoDecoder,
    # 524: DiscussionUpdateDecoder,
    # 528: MsgType0x210Decoder,
    # 529: MsgType0x211Decoder,
    # 562: VideoQCallDecoder,
    # 732: MsgType0x2dcDecoder,
    # 734: SharpVideoDecoder,
}
"""C2C Message Decoders.

Note:
    Source: com.tencent.mobileqq.app.QQMessageFacadeConfig.start
"""
