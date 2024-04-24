from typing import Union
from fastapi import FastAPI,Response,Request,HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3

app = FastAPI()

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/mahasiswa/{nim}")
def ambil_mhs(nim:str):
    return {"nama": "Budi Martami"}

@app.get("/mahasiswa2/")
def ambil_mhs2(nim:str):
    return {"nama": "Budi Martami 2"}

@app.get("/daftar_mhs/")
def daftar_mhs(id_prov:str,angkatan:str):
    return {"query":" idprov: {}  ; angkatan: {} ".format(id_prov,angkatan),"data":[{"nim":"1234"},{"nim":"1235"}]}

# panggil sekali saja
@app.get("/init/")
def init_db():
    con = None
    try:
        DB_NAME = "upi.db"
        con = sqlite3.connect(DB_NAME)
        cur = con.cursor()
        create_table = """ CREATE TABLE IF NOT EXISTS mahasiswa(
                ID      	INTEGER PRIMARY KEY 	AUTOINCREMENT,
                nim     	TEXT            	NOT NULL,
                nama    	TEXT            	NOT NULL,
                id_prov 	TEXT            	NOT NULL,
                angkatan	TEXT            	NOT NULL,
                tinggi_badan  INTEGER
            )  
            """
        cur.execute(create_table)
        con.commit()
    except Exception as e:
        return {"status": f"terjadi error: {e}"}
    finally:
        if con:
            con.close()  # Ensure the connection is closed even if an error occurs

    return {"status": "ok, db dan tabel berhasil dicreate"}


from pydantic import BaseModel

from typing import Optional

class Mhs(BaseModel):
    nim: str
    nama: str
    id_prov: str
    angkatan: str
    tinggi_badan: Optional[int] | None = None  # yang boleh null hanya ini


#status code 201 standard return creation
#return objek yang baru dicreate (response_model tipenya Mhs)
@app.post("/tambah_mhs/", response_model=Mhs, status_code=201)
def tambah_mhs(m: Mhs):
    try:
        DB_NAME = "upi.db"
        con = sqlite3.connect(DB_NAME)
        cur = con.cursor()
        cur.execute("INSERT INTO mahasiswa (nim, nama, id_prov, angkatan, tinggi_badan) VALUES (?, ?, ?, ?, ?)",
                    (m.nim, m.nama, m.id_prov, m.angkatan, m.tinggi_badan))
        con.commit()
    except sqlite3.Error as e:
        print("Error dalam operasi database:", e)
        # Mengembalikan data yang dimasukkan meskipun terjadi pengecualian
        return m
    except Exception as e:
        print("Error lain:", e)
        # Mengembalikan data yang dimasukkan meskipun terjadi pengecualian
        return m
    finally:
        con.close()
    return m



@app.get("/tampilkan_semua_mhs/")
def tampil_semua_mhs():
    try:
        DB_NAME = "upi.db"
        con = sqlite3.connect(DB_NAME)
        cur = con.cursor()
        recs = []
        for row in cur.execute("SELECT * FROM mahasiswa"):
            recs.append(row)
    except:
        return {"status": "terjadi error"}
    finally:
        con.close()
    return {"data": recs}

from fastapi.encoders import jsonable_encoder


@app.put("/update_mhs_put/{nim}", response_model=Mhs)
def update_mhs_put(response: Response, nim: str, m: Mhs):
    # update keseluruhan
    # karena key, nim tidak diupdate
    try:
        DB_NAME = "upi.db"
        con = sqlite3.connect(DB_NAME)
        cur = con.cursor()
        cur.execute("SELECT * FROM mahasiswa WHERE nim = ?", (nim,))  # tambah koma untuk menandakan tuple
        existing_item = cur.fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Terjadi exception: {}".format(str(e)))

    if existing_item:  # data ada
        print(m.tinggi_badan)
        # Menggunakan parameter binding untuk menghindari SQL injection
        cur.execute("UPDATE mahasiswa SET nama = ?, id_prov = ?, angkatan = ?, tinggi_badan = ? WHERE nim = ?",
                    (m.nama, m.id_prov, m.angkatan, m.tinggi_badan, nim))
        con.commit()
        response.headers["Location"] = "/mahasiswa/{}".format(m.nim)
    else:  # data tidak ada
        print("item not found")
        raise HTTPException(status_code=404, detail="Item Not Found")

    con.close()
    return m


# khusus untuk patch, jadi boleh tidak ada
# menggunakan "kosong" dan -9999 supaya bisa membedakan apakah tdk diupdate ("kosong") atau mau
# diupdate dengan dengan None atau 0
class MhsPatch(BaseModel):
    nama: str | None = "kosong"
    id_prov: str | None = "kosong"
    angkatan: str | None = "kosong"
    tinggi_badan: Optional[int] | None = -9999  # yang boleh null hanya ini


@app.patch("/update_mhs_patch/{nim}", response_model=MhsPatch)
def update_mhs_patch(response: Response, nim: str, m: MhsPatch):
    try:
        DB_NAME = "upi.db"
        con = sqlite3.connect(DB_NAME)
        cur = con.cursor()
        cur.execute("SELECT * FROM mahasiswa WHERE nim = ?", (nim,))
        existing_item = cur.fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Terjadi exception: {}".format(str(e)))

    if existing_item:
        columns = []
        values = []
        if m.nama != "kosong":
            columns.append("nama")
            values.append(m.nama if m.nama else None)
        if m.angkatan != "kosong":
            columns.append("angkatan")
            values.append(m.angkatan if m.angkatan else None)
        if m.id_prov != "kosong":
            columns.append("id_prov")
            values.append(m.id_prov if m.id_prov else None)
        if m.tinggi_badan != -9999:
            columns.append("tinggi_badan")
            values.append(m.tinggi_badan if m.tinggi_badan else None)

        if columns:
            set_clause = ", ".join([f"{col} = ?" for col in columns])
            sqlstr = f"UPDATE mahasiswa SET {set_clause} WHERE nim = ?"
            values.append(nim)
            try:
                cur.execute(sqlstr, values)
                con.commit()
                response.headers["Location"] = "/mahasiswa/{}".format(nim)
            except Exception as e:
                raise HTTPException(status_code=500, detail="Terjadi exception: {}".format(str(e)))
    else:
        raise HTTPException(status_code=404, detail="Item Not Found")

    con.close()
    return m

    
@app.delete("/delete_mhs/{nim}")
def delete_mhs(nim: str):
    try:
        DB_NAME = "upi.db"
        con = sqlite3.connect(DB_NAME)
        cur = con.cursor()
        sqlstr = "delete from mahasiswa  where nim='{}'".format(nim)                 
        print(sqlstr) # debug 
        cur.execute(sqlstr)
        con.commit()
    except:
        return ({"status":"terjadi error"})   
    finally:  	 
        con.close()
    
    return {"status":"ok"}


from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
import os

app = FastAPI()


@app.post("/uploadImage")
async def upload_image(file: UploadFile = File(...)):
    try:

        print("Mulai Upload")
        print(f"Filename: {file.filename}")
        contents = await file.read()

        data_file_path = "../data_file/"
        if not os.path.exists(data_file_path):
            os.makedirs(data_file_path)

        with open(data_file_path + file.filename, "wb") as f:
            f.write(contents)

        return {"message": f"Upload berhasil: {file.filename}"}

    except Exception as e:
        return {"message": f"Error uploading file: {str(e)}"}

    finally:
        await file.close()


@app.get("/getimage/{nama_file}")
async def get_image(nama_file: str):
    data_file_path = "../data_file/"  
    file_path = os.path.join(data_file_path, nama_file)
    if os.path.exists(file_path):
        # Return the file response
        return FileResponse(file_path)
    else:
        return {"message": "File not found"}
