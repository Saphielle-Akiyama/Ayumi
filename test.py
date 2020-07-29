import discord
from discord.ext import commands

bot = commands.Bot(command_prefix='s--')

class Converter(commands.Converter):
    async def convert(self, ctx, arg):
        return []


@bot.command()
async def foo(ctx, *arg: commands.Greedy[Converter]):
    await ctx.send(arg)

bot.run('NzExNjkzMDQxMTM1Nzc5ODgy.Xvx30Q.ult1ljw-kx4Vfm-r4yLBOMWI51g')
