import discord
import audioop
import traceback
import struct

class Mixer(discord.AudioSource):
    def __init__(self):
        self.channels = {}

    def get_channel(self, channel_str: str):
        channel = self.channels.get(channel_str)
        if channel: return channel
        else: channel = []
        self.channels[channel_str] = channel
        return channel

    def add_audio_source(self, channel_str: str, audio: discord.AudioSource) -> None:
        channel = self.get_channel(channel_str)
        try: channel.append(audio)
        except Exception as e: print(f"Mixer {id(self)} Exception While Appending: {e}")

    def remove_audio_source(self, channel_str: str, audio: discord.AudioSource) -> None:
        channel = self.get_channel(channel_str)
        try: channel.remove(audio)
        except Exception as e: print(f"Mixer {id(self)} Exception While Removing: {e}")

    def mix_pcm_16bit(self, pcm1: bytes, pcm2: bytes) -> bytes:
        mixed_pcm = bytearray()

        for i in range(0, 3840, 2):  # Step by 2 because it's 16-bit (2 bytes per sample)
            # Unpack 16-bit samples (little-endian, signed)
            sample1 = struct.unpack_from("<h", pcm1, i)[0]
            sample2 = struct.unpack_from("<h", pcm2, i)[0]

            # Mix the samples (prevent overflow by keeping within int16 range)
            mixed_sample = max(min(sample1 + sample2, 32767), -32768)

            # Pack back into little-endian bytes and add to output
            mixed_pcm.extend(struct.pack("<h", mixed_sample))

        return bytes(mixed_pcm)

    def read(self):
        output = None
        channels = self.channels.values()
        for channel in channels:
            for audio_source_index in range(len(channel) - 1, -1, -1):
                audio_source = channel[audio_source_index]
                audio_source_output = audio_source.read()
                if audio_source_output == b'':
                    del channel[audio_source_index]
                    continue
                if output: output = self.mix_pcm_16bit(output, audio_source_output)
                else: output = audio_source_output
        if not output: output = b"\x00" * 3840
        return output
    
    def is_opus(self):
        return False