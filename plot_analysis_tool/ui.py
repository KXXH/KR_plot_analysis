from tkinter import *
from tkinter import filedialog
from tkinter import ttk
from tkinter import messagebox
import json

from movie_tokenizer import Movie_Tokenizer

root = Tk()
root.title("剧情分词工具")

selected_name = None
selected_index = None


mt = Movie_Tokenizer()


def refresh_plot_text():
    plot_text.delete("1.0", END)
    texts = mt.text
    plot_text.insert(INSERT, texts)


def refresh_splited_text():
    splited_text.delete("1.0", END)
    text = "\n".join(mt.splited_result)
    splited_text.insert(INSERT, text)


def refresh_cut_text():
    cut_text.delete("1.0", END)
    text = "\n".join("/".join(words) for words in mt.cut())
    cut_text.insert(INSERT, text)


def refresh_name():
    name_list.delete(0, END)
    for name in mt.get_names():
        name_list.insert(0, name)


def refresh_alias(name=None):
    alias_list.delete(0, END)
    if name is None:
        return
    for alias in mt.get_alias(name):
        alias_list.insert(0, alias)


def show_alias_cmd():
    global selected_name, selected_index
    selected_index = name_list.curselection()
    selected_name = name_list.get(selected_index)
    name_label_val.set(selected_name)
    refresh_alias(selected_name)


def add_alias_cmd():
    global selected_name
    if selected_name is None:
        tkinter.messagebox.showinfo(message="你还没有选定角色!")
        return
    alias = alias_entry.get()
    alias_entry.delete(0, END)
    mt.add_alias(selected_name, alias)
    refresh_alias(selected_name)


def add_name_cmd():
    name = name_entry.get()
    name_entry.delete(0, END)
    mt.add_name(name)
    refresh_name()


def del_name_cmd():
    global selected_index, selected_name
    if selected_index is None:
        messagebox.showinfo(message="你还没有选定角色!")
        return
    if messagebox.askyesno(message="删除角色后无法恢复，继续?"):
        mt.del_name(selected_name)
        refresh_name()
        refresh_alias()
        name_label_val.set("没有选中角色")
        selected_name, selected_index = None, None


def del_alias_cmd():
    global selected_name
    selected_alias = alias_list.get(alias_list.curselection())
    mt.del_alias(selected_name, selected_alias)
    refresh_alias(selected_name)


def get_co_present():
    co_present = mt.co_present()
    top_l = Toplevel(root)
    top_l.title("共现矩阵")
    columns = list(co_present.keys())
    matrix_table = ttk.Treeview(
        top_l, columns=["#", *columns], show="headings")
    matrix_table.column("#", width=70)
    matrix_table.heading("#", text="角色")
    for column in columns:
        matrix_table.column(column, width=70)
        matrix_table.heading(column, text=column)
    for key, value in co_present.items():
        data = list(value[item] for item in columns)
        matrix_table.insert("", "end", values=[key, *data])
    matrix_table.pack()


def export_names():
    j = dict(mt.name_dict)
    for key in j:
        j[key] = list(j[key])
    filename = filedialog.asksaveasfilename(
        title="保存角色信息文件", filetypes=[("JSON文件", "*.json")], defaultextension="json")
    if not filename:
        return
    with open(filename, "w") as f:
        f.write(json.dumps(j))
    messagebox.showinfo(message=f"已成功导出角色信息文件到{filename}")


def import_names():
    filename = filedialog.askopenfilename(title="打开角色信息文件")
    if not filename:
        return
    with open(filename, "r", encoding="utf8") as f:
        j = json.loads(f.read())
    for key in j:
        j[key] = set(j[key])
    mt.import_name_dict(j)
    refresh_name()
    refresh_alias()
    messagebox.showinfo(message=f"{filename}已成功导入")


def export_co_present():
    matrix = mt.co_present()
    filename = filedialog.asksaveasfilename(
        title="导出共现矩阵", filetypes=[("JSON文件", "*.json")], defaultextension="json")
    if not filename:
        return
    with open(filename, "w") as f:
        f.write(json.dumps(matrix))
    messagebox.showinfo(message=f"已成功导出至{filename}")


def import_stopwords():
    filename = filedialog.askopenfilename(
        title="读取停用词", filetypes=[("文本文件", "*.txt")])
    if not filename:
        return
    mt.import_stopwords(filename)
    messagebox.showinfo(message=f"成功从文件{filename}导入停用词!")


def import_plot():
    filename = filedialog.askopenfilename(
        title="打开剧情文件", filetypes=[("文本文件", "*.txt")])
    if not filename:
        return
    with open(filename, "r", encoding="utf8") as f:
        text = f.read()
    mt.set_text(text)
    refresh_plot_text()


def export_cut():
    text = plot_text.get("1.0", END)
    mt.set_text(text)
    cut_result = mt.cut()
    filename = filedialog.asksaveasfilename(
        title="导出分词结果", defaultextension="json", filetypes=[("JSON文件", "*.json")])
    if not filename:
        return
    with open(filename, "w") as f:
        f.write(json.dumps(cut_result))
    messagebox.showinfo(message=f"成功导出分词结果至f{filename}!")


def show_word_freq():
    text = plot_text.get("1.0", END)
    mt.set_text(text)
    freq = mt.word_freq()
    freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    top_l = Toplevel(root)
    top_l.title("词频表")
    columns = ["词语", "出现次数"]
    freq_table = ttk.Treeview(
        top_l, columns=columns, show="headings")
    for column in columns:
        freq_table.column(column, width=70)
        freq_table.heading(column, text=column)
    for item in freq:
        freq_table.insert("", "end", values=item)
    freq_table.pack()


def export_word_freq():
    text = plot_text.get("1.0", END)
    mt.set_text(text)
    freq = mt.word_freq()
    filename = filedialog.asksaveasfilename(
        title="导出词频文件", filetypes=[("JSON文件", "*.json")], defaultextension="json")
    if not filename:
        return
    with open(filename, "w") as f:
        f.write(json.dumps(freq))
    messagebox.showinfo(message=f"成功导出词频数据至{filename}!")


def initialize():
    mt.initialize_tokenizer()
    messagebox.showinfo(message="重置分词器成功!")


def tab_switch_callback(event):
    index = main_ntb.index(main_ntb.select())
    if index == 0:
        pass
    elif index == 1:
        text = plot_text.get("1.0", END)
        mt.set_text(text)
        refresh_splited_text()
    elif index == 2:
        text = plot_text.get("1.0", END)
        mt.set_text(text)
        refresh_cut_text()


main_ntb = ttk.Notebook(root)

plot_text = Text(main_ntb)
splited_text = Text(main_ntb)
cut_text = Text(main_ntb)

#plot_text.pack(fill="x", side="top")
main_ntb.add(plot_text, text="文字编辑")
main_ntb.add(splited_text, text="分句")
main_ntb.add(cut_text, text="分词")
main_ntb.pack(expand=True)

main_ntb.bind("<<NotebookTabChanged>>", tab_switch_callback)

control_frame = Frame(root)

control_frame.pack(expand=True)

menu = Menu(root)

plot_menu = Menu(menu, tearoff=0)
menu.add_cascade(label="剧情数据", menu=plot_menu)
plot_menu.add_command(label="打开剧情文件", command=import_plot)

name_menu = Menu(menu, tearoff=0)
menu.add_cascade(label="角色数据", menu=name_menu)
name_menu.add_command(label="导出角色数据", command=export_names)
name_menu.add_command(label="导入角色数据", command=import_names)


co_present_menu = Menu(menu, tearoff=0)
menu.add_cascade(label="共现矩阵", menu=co_present_menu)
co_present_menu.add_command(label="显示共现矩阵", command=get_co_present)
co_present_menu.add_command(label="导出共现矩阵", command=export_co_present)

cut_menu = Menu(menu, tearoff=0)
menu.add_cascade(label="分词", menu=cut_menu)
cut_menu.add_command(label="载入停用词库", command=import_stopwords)
cut_menu.add_command(label="重置分词器", command=initialize)
cut_menu.add_command(label="查看词频(不含停用词)", command=show_word_freq)
cut_menu.add_command(label="导出分词结果", command=export_cut)


alias_list = Listbox(root)
name_list = Listbox(root)
refresh_name()

name_list.pack(side="left")
alias_list.pack(side="left")

name_control_frame = Frame(root)
name_control_frame.pack(expand=True)

name_entry = Entry(name_control_frame)
name_label_val = StringVar()
name_label_val.set("没有选中角色")
name_label = Label(name_control_frame, textvariable=name_label_val)

alias_entry = Entry(name_control_frame)
show_alias_btn = Button(name_control_frame, text="选中角色",
                        command=show_alias_cmd)
add_name_btn = Button(name_control_frame, text="添加角色", command=add_name_cmd)
add_alias_btn = Button(name_control_frame, text="添加别名", command=add_alias_cmd)
del_name_btn = Button(name_control_frame, text="删除角色", command=del_name_cmd)
del_alias_btn = Button(name_control_frame, text="删除别名", command=del_alias_cmd)

show_alias_btn.grid(row=0, column=0)
name_label.grid(row=0, column=1)

name_entry.grid(row=1, column=0, columnspan=2)
add_name_btn.grid(row=2, column=0)
del_name_btn.grid(row=2, column=1)

alias_entry.grid(row=3, column=0, columnspan=2)
add_alias_btn.grid(row=4, column=0)
del_alias_btn.grid(row=4, column=1)

root.config(menu=menu)
root.mainloop()
